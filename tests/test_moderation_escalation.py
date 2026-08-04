"""
Tests for:
- Auto Warn -> Auto Ban Escalation (ban instead of mute once warn_ban_threshold
  is reached, opt-in via autobanwarns)
- Auto Pin Announcements (admin message starting with the configured tag
  gets pinned automatically, opt-in via autopin)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import handlers.moderation as moderation


def _make_update_and_context():
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.message_id = 42
    update.effective_chat.id = -100123
    update.effective_user.id = 777
    context = MagicMock()
    context.bot.id = 1
    context.bot.ban_chat_member = AsyncMock()
    context.bot.restrict_chat_member = AsyncMock()
    context.bot.pin_chat_message = AsyncMock()
    return update, context


@pytest.mark.asyncio
async def test_finalize_warn_bans_when_threshold_reached_and_feature_on():
    update, context = _make_update_and_context()
    settings = {"auto_ban_on_warns_enabled": True, "warn_ban_threshold": 5}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)), \
         patch("modules.moderation_extra.log_action", new=AsyncMock()) as mock_log:
        await moderation._finalize_warn(update, context, -100123, 555, "Target", "spamming", 5)

    context.bot.ban_chat_member.assert_awaited_once_with(-100123, 555)
    context.bot.restrict_chat_member.assert_not_awaited()
    mock_log.assert_awaited_once()
    update.message.reply_text.assert_awaited_once()
    assert "auto-banned" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_finalize_warn_mutes_when_below_ban_threshold():
    update, context = _make_update_and_context()
    settings = {"auto_ban_on_warns_enabled": True, "warn_ban_threshold": 5}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)):
        await moderation._finalize_warn(update, context, -100123, 555, "Target", "spamming", 3)

    context.bot.ban_chat_member.assert_not_awaited()
    context.bot.restrict_chat_member.assert_awaited_once()
    assert "muted" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_finalize_warn_ignores_ban_threshold_when_feature_off():
    update, context = _make_update_and_context()
    settings = {"auto_ban_on_warns_enabled": False, "warn_ban_threshold": 5}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)):
        await moderation._finalize_warn(update, context, -100123, 555, "Target", "spamming", 5)

    context.bot.ban_chat_member.assert_not_awaited()
    context.bot.restrict_chat_member.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_warn_plain_warn_below_mute_limit():
    update, context = _make_update_and_context()
    settings = {"auto_ban_on_warns_enabled": False, "warn_ban_threshold": 5}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)):
        await moderation._finalize_warn(update, context, -100123, 555, "Target", "spamming", 1)

    context.bot.ban_chat_member.assert_not_awaited()
    context.bot.restrict_chat_member.assert_not_awaited()
    assert "warned (1/" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_auto_pin_pins_tagged_admin_message_when_enabled():
    update, context = _make_update_and_context()
    update.message.text = "#pin Meeting moved to 5pm"
    update.effective_message = update.message
    settings = {"auto_pin_announcements_enabled": True, "auto_pin_tag": "#pin", "word_filter_enabled": False}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)), \
         patch.object(moderation, "_is_group_admin", new=AsyncMock(return_value=True)), \
         patch("modules.moderation_extra.log_action", new=AsyncMock()), \
         patch.object(moderation, "auto_moderate", new=AsyncMock(return_value=False)):
        await moderation.handle_group_text(update, context)

    context.bot.pin_chat_message.assert_awaited_once_with(-100123, 42)


@pytest.mark.asyncio
async def test_auto_pin_skipped_when_sender_not_admin():
    update, context = _make_update_and_context()
    update.message.text = "#pin not an admin"
    update.effective_message = update.message
    settings = {"auto_pin_announcements_enabled": True, "auto_pin_tag": "#pin", "word_filter_enabled": False}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)), \
         patch.object(moderation, "_is_group_admin", new=AsyncMock(return_value=False)), \
         patch.object(moderation, "auto_moderate", new=AsyncMock(return_value=False)):
        await moderation.handle_group_text(update, context)

    context.bot.pin_chat_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_pin_skipped_when_feature_disabled():
    update, context = _make_update_and_context()
    update.message.text = "#pin hello"
    update.effective_message = update.message
    settings = {"auto_pin_announcements_enabled": False, "auto_pin_tag": "#pin", "word_filter_enabled": False}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)), \
         patch.object(moderation, "auto_moderate", new=AsyncMock(return_value=False)):
        await moderation.handle_group_text(update, context)

    context.bot.pin_chat_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_pin_skipped_when_message_not_tagged():
    update, context = _make_update_and_context()
    update.message.text = "just a regular message"
    update.effective_message = update.message
    settings = {"auto_pin_announcements_enabled": True, "auto_pin_tag": "#pin", "word_filter_enabled": False}

    with patch.object(moderation.mod, "get_settings", new=AsyncMock(return_value=settings)), \
         patch.object(moderation, "auto_moderate", new=AsyncMock(return_value=False)):
        await moderation.handle_group_text(update, context)

    context.bot.pin_chat_message.assert_not_awaited()
