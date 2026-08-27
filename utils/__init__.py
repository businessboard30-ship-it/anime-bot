"""
Utility functions for the Telegram bot
"""

from config import ADMIN_ID
from telegram.error import BadRequest


def is_founder(user_id: int) -> bool:
    """Check if user is the bot founder/admin (main bot's ADMIN_ID env var only)."""
    return ADMIN_ID is not None and user_id == ADMIN_ID


def is_owner(user_id: int, context=None) -> bool:
    """
    Full owner check: true if this user is the main bot's founder (ADMIN_ID),
    OR — when running as a cloned bot — the owner of THIS clone
    (bot_data['clone_config']['owner_id'], set in api/bot.py get_clone_application).

    Every paid-feature gate should use this instead of is_founder() directly,
    so clone owners get full access on their own clone, not just the single
    global admin on the main bot.
    """
    if is_founder(user_id):
        return True
    if context is not None:
        bot_data = getattr(context, "bot_data", None)
        clone_config = bot_data.get("clone_config") if bot_data else None
        if clone_config and clone_config.get("owner_id") == user_id:
            return True
    return False


async def safe_send_message(bot_or_message, text: str, reply_markup=None, parse_mode=None, chat_id=None):
    """
    Send a message that can NEVER crash the caller due to a Markdown entity
    error (e.g. an unescaped underscore in a name/username sourced from user
    input or an env var we don't fully control). Tries the formatted version
    first; on a "can't parse entities" failure, strips parse_mode and Markdown
    formatting characters and resends as plain text instead of raising.

    Pass either:
      - a Message object (uses message.reply_text) — chat_id not needed
      - a Bot object + chat_id (uses bot.send_message)
    """
    from telegram.error import BadRequest

    async def _send(txt, pm):
        if chat_id is not None:
            return await bot_or_message.send_message(chat_id=chat_id, text=txt, reply_markup=reply_markup, parse_mode=pm)
        return await bot_or_message.reply_text(txt, reply_markup=reply_markup, parse_mode=pm)

    try:
        return await _send(text, parse_mode)
    except BadRequest as e:
        if "can't parse entities" in str(e).lower() or "can't find end" in str(e).lower():
            plain = text.replace("*", "").replace("_", "").replace("`", "")
            return await _send(plain, None)
        raise


async def safe_edit_message(query, text: str, reply_markup=None, parse_mode=None):
    """
    Edit a callback query's message regardless of whether the original message
    was plain text or had media (photo/video/animation/document) attached.

    query.edit_message_text() throws "There is no text in the message to edit"
    on any message that has media, because media messages carry a caption, not
    text — this happens whenever a button is tapped on a broadcast, since
    broadcasts are frequently sent as photos. Use this helper anywhere a button
    might be attached to a message that isn't guaranteed to be text-only
    (e.g. broadcast keyboards) instead of calling edit_message_text directly.
    """
    has_media = bool(getattr(query.message, "photo", None) or
                      getattr(query.message, "video", None) or
                      getattr(query.message, "animation", None) or
                      getattr(query.message, "document", None))
    try:
        if has_media:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        # Telegram throws this when the new text/markup is byte-for-byte
        # identical to what's already shown (e.g. double-tapping a button
        # that redraws the same menu). It's a no-op, not a real failure —
        # swallow it instead of letting it bubble up as a fake "Bot error"
        # admin alert.
        if "message is not modified" not in str(e).lower():
            raise


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for MarkdownV2 parse mode.
    """
    if not text:
        return text
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def escape_markdown_v1(text: str) -> str:
    """
    Escape special characters for Markdown (v1) parse mode.
    """
    if not text:
        return text
    special_chars = r'_*[]()~`'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def safe_markdown_message(text: str, parse_mode: str = "Markdown") -> str:
    """
    Safely escape user-generated content for Markdown.
    """
    if parse_mode == "MarkdownV2":
        return escape_markdown_v2(text)
    else:
        return escape_markdown_v1(text)
