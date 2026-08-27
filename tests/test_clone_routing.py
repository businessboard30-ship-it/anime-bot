import conftest  # noqa: F401
from unittest.mock import AsyncMock, patch

import pytest

import bot as bot_module  # api/bot.py, loaded via tests/conftest.py's sys.path insert


def _make_clone_row(clone_id, bot_username, secret, branding):
    return {
        "clone_id": clone_id,
        "owner_id": 1000 + clone_id,
        "bot_name": f"Clone{clone_id}",
        "bot_token": f"{clone_id}0000:fake-token-for-clone-{clone_id}",
        "bot_username": bot_username,
        "webhook_secret": secret,
        "custom_data": {"branding": branding},
        "status": "active",
    }


@pytest.fixture(autouse=True)
def reset_clone_caches():
    """Every test starts from a clean warm-container cache, since these are module-level dicts."""
    bot_module._clone_apps.clear()
    bot_module._clone_apps_initialized.clear()
    yield
    bot_module._clone_apps.clear()
    bot_module._clone_apps_initialized.clear()


@pytest.mark.asyncio
async def test_isolation_two_clones_get_distinct_bot_data():
    """
    3.4 isolation test: with two clones active, each must get its own
    bot_data["clone_config"] — this is the exact test that catches a bot_data
    wiring mistake that would otherwise leak one customer's branding into
    another's bot, silently, in production.
    """
    clone_a = _make_clone_row(1, "CloneOneBot", "secretA", "Shonen only")
    clone_b = _make_clone_row(2, "CloneTwoBot", "secretB", "Isekai only")

    async def fake_get_clone_for_routing(clone_id):
        return {1: clone_a, 2: clone_b}.get(clone_id)

    with patch.object(bot_module.db, "get_clone_for_routing", side_effect=fake_get_clone_for_routing):
        app_a, _ = await bot_module.get_clone_application(1)
        app_b, _ = await bot_module.get_clone_application(2)

    assert app_a is not app_b
    assert app_a.bot_data["clone_config"]["clone_id"] == 1
    assert app_b.bot_data["clone_config"]["clone_id"] == 2
    assert app_a.bot_data["clone_config"]["branding"] == "Shonen only"
    assert app_b.bot_data["clone_config"]["branding"] == "Isekai only"
    assert app_a.bot_data is not app_b.bot_data


@pytest.mark.asyncio
async def test_secret_scoping_clone_a_secret_does_not_validate_clone_b():
    """
    3.4 secret-scoping test: clone A's webhook secret must not validate a
    forged request claiming to be clone B.
    """
    clone_a = _make_clone_row(1, "CloneOneBot", "secretA", "Shonen only")
    clone_b = _make_clone_row(2, "CloneTwoBot", "secretB", "Isekai only")

    async def fake_get_clone_for_routing(clone_id):
        return {1: clone_a, 2: clone_b}.get(clone_id)

    handler_instance = bot_module.handler.__new__(bot_module.handler)

    with patch.object(bot_module.db, "get_clone_for_routing", side_effect=fake_get_clone_for_routing), \
         patch.object(bot_module, "process_update", new=AsyncMock()) as mock_process:
        # Forged: claims to be clone B's traffic (clone_id=2) but presents clone A's secret.
        await handler_instance._handle_clone_update(2, "secretA", {"update_id": 1})
        mock_process.assert_not_called()

        # Correct: clone B's own secret against clone_id=2 works.
        await handler_instance._handle_clone_update(2, "secretB", {"update_id": 2})
        mock_process.assert_called_once_with({"update_id": 2}, clone_id=2)


@pytest.mark.asyncio
async def test_deactivated_clone_is_rejected_even_with_warm_cache():
    """
    3.4 deactivation test: once a clone is deactivated, a replayed/old update
    for that clone_id must be rejected, not silently processed — even if a
    warm container still has that clone's Application cached from earlier.
    """
    clone_a = _make_clone_row(1, "CloneOneBot", "secretA", "Shonen only")
    call_state = {"active": True}

    async def fake_get_clone_for_routing(clone_id):
        if clone_id == 1 and call_state["active"]:
            return clone_a
        return None  # deactivated -> not returned as active

    handler_instance = bot_module.handler.__new__(bot_module.handler)

    with patch.object(bot_module.db, "get_clone_for_routing", side_effect=fake_get_clone_for_routing):
        await bot_module.get_clone_application(1)
        assert 1 in bot_module._clone_apps

        call_state["active"] = False

        with patch.object(bot_module, "process_update", new=AsyncMock()) as mock_process:
            await handler_instance._handle_clone_update(1, "secretA", {"update_id": 99})
            mock_process.assert_not_called()


@pytest.mark.asyncio
async def test_lru_cache_evicts_oldest_clone_application():
    """Part 3.1: the per-clone Application cache is bounded, not unbounded."""
    original_cap = bot_module.CLONE_APP_CACHE_SIZE
    bot_module.CLONE_APP_CACHE_SIZE = 2
    try:
        clones = {i: _make_clone_row(i, f"Clone{i}Bot", f"secret{i}", f"branding{i}") for i in range(1, 4)}

        async def fake_get_clone_for_routing(clone_id):
            return clones.get(clone_id)

        with patch.object(bot_module.db, "get_clone_for_routing", side_effect=fake_get_clone_for_routing):
            await bot_module.get_clone_application(1)
            await bot_module.get_clone_application(2)
            await bot_module.get_clone_application(3)  # should evict clone 1 (oldest, cap=2)

        assert 1 not in bot_module._clone_apps
        assert 2 in bot_module._clone_apps
        assert 3 in bot_module._clone_apps
    finally:
        bot_module.CLONE_APP_CACHE_SIZE = original_cap
