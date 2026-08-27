"""
Tests for Auto-DM on Join Request (autodmjoin):
- Only acts when the group has autodmjoin turned on
- DMs the requester the main menu, then approves the request
- A failed DM never blocks approval (approve happens either way)
- Logs the outcome either way
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.error import TelegramError

import handlers.moderation as moderation


def _make_join_request_update(clone_config=None):
    request = MagicMock()
    request.chat.id = -100999
    request.chat.title = "Test Group"
    request.from_user.id = 42
    request.from_user.first_name = "Ama"

    update = MagicMock()
    update.chat_join_request = request

    context = MagicMock()
    context.bot.id = 1
    context.bot.send_message = AsyncMock()
    context.bot.approve_chat_join_request = AsyncMock()
    context.bot_data = {"clone_config": clone_config} if clone_config is not None else {}

    return update, context


@pytest.mark.asyncio
async def test_join_request_ignored_when_feature_off():
    update, context = _make_join_request_update()
    settings = {"auto_dm_on_join_enabled": False}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)):
        await moderation.handle_join_request(update, context)

    context.bot.send_message.assert_not_awaited()
    context.bot.approve_chat_join_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_join_request_dms_and_approves_when_enabled():
    update, context = _make_join_request_update()
    settings = {"auto_dm_on_join_enabled": True}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)), \
         patch("modules.moderation_extra.log_action", new=AsyncMock()) as mock_log:
        await moderation.handle_join_request(update, context)

    context.bot.send_message.assert_awaited_once()
    assert context.bot.send_message.call_args[0][0] == 42
    context.bot.approve_chat_join_request.assert_awaited_once_with(-100999, 42)
    mock_log.assert_awaited_once()
    assert mock_log.call_args.kwargs.get("reason") == "DM sent" or mock_log.call_args[0]


@pytest.mark.asyncio
async def test_join_request_approves_even_when_dm_fails():
    update, context = _make_join_request_update()
    context.bot.send_message = AsyncMock(side_effect=TelegramError("Forbidden: bot can't initiate conversation"))
    settings = {"auto_dm_on_join_enabled": True}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)), \
         patch("modules.moderation_extra.log_action", new=AsyncMock()) as mock_log:
        await moderation.handle_join_request(update, context)

    context.bot.approve_chat_join_request.assert_awaited_once_with(-100999, 42)
    logged_reason = mock_log.call_args.kwargs.get("reason", "")
    assert "DM failed" in logged_reason


@pytest.mark.asyncio
async def test_join_request_uses_clone_branding_when_present():
    update, context = _make_join_request_update(clone_config={"name": "MyCloneBot"})
    settings = {"auto_dm_on_join_enabled": True}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)), \
         patch("modules.moderation_extra.log_action", new=AsyncMock()):
        await moderation.handle_join_request(update, context)

    sent_text = context.bot.send_message.call_args[0][1]
    assert "MyCloneBot" in sent_text
