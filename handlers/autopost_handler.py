"""
Autopost / recurring posts.

Ported + extended from superbot.py's recurring_post_job / cmd_setrecurring /
cmd_stoprecurring. The original was an in-process scheduler loop; this
deployment is a stateless Vercel webhook, so the actual sending happens in
api/cron_autopost.py, triggered externally on a schedule. This module only
handles the conversational setup (command -> ask interval -> ask content ->
save row) and the list/stop commands.

Two ways to register a recurring post (per product decision: "both"):
  1. In the target group/channel itself, by a chat admin: /setrecurring 30m
  2. From a DM, by the bot owner, targeting any chat_id directly:
     /setrecurring -1001234567890 2h
"""
import re
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID, EMOJI_COLORS
from database import db
import flow_state
from handlers.moderation import _is_group_admin

logger = logging.getLogger(__name__)

_INTERVAL_RE = re.compile(r"^(\d+)\s*(m|min|mins|minutes|h|hr|hrs|hours)$", re.IGNORECASE)


def _clone_id(context) -> int:
    """0 for the main bot, else the running clone's id."""
    clone_config = context.bot_data.get("clone_config")
    return clone_config.get("clone_id") if clone_config else 0


def _parse_interval(raw: str) -> Optional[int]:
    """Parse '30m', '2h', '45 minutes', etc. into a whole number of minutes."""
    m = _INTERVAL_RE.match(raw.strip())
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("h"):
        return n * 60
    return n


async def cmd_setrecurring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /setrecurring 30m           -> in a group/channel, by a group admin
    /setrecurring <chat_id> 2h  -> in DM, by the bot owner
    """
    user_id = update.effective_user.id
    args = context.args or []
    chat = update.effective_chat

    if chat.type in ("group", "supergroup", "channel"):
        if not await _is_group_admin(update, context, user_id) and user_id != ADMIN_ID:
            await update.message.reply_text("Only an admin of this chat can set up autopost here.")
            return
        if len(args) != 1:
            await update.message.reply_text(
                "Usage: /setrecurring <interval>\nExamples: /setrecurring 30m  or  /setrecurring 2h"
            )
            return
        interval_minutes = _parse_interval(args[0])
        if interval_minutes is None or interval_minutes < 1:
            await update.message.reply_text("Couldn't parse that interval. Use e.g. 30m, 45m, 2h.")
            return
        target_chat_id = chat.id

    elif chat.type == "private":
        if user_id != ADMIN_ID:
            await update.message.reply_text(
                "To set up autopost in a group, run /setrecurring there as that group's admin.\n"
                "Registering a chat by ID from DM is restricted to the bot owner."
            )
            return
        if len(args) != 2:
            await update.message.reply_text(
                "Usage: /setrecurring <chat_id> <interval>\nExample: /setrecurring -1001234567890 2h"
            )
            return
        try:
            target_chat_id = int(args[0])
        except ValueError:
            await update.message.reply_text("First argument must be a numeric chat_id.")
            return
        interval_minutes = _parse_interval(args[1])
        if interval_minutes is None or interval_minutes < 1:
            await update.message.reply_text("Couldn't parse that interval. Use e.g. 30m, 45m, 2h.")
            return
    else:
        await update.message.reply_text("Autopost isn't supported in this chat type.")
        return

    context.user_data["mode"] = "autopost_await_content"
    context.user_data["autopost_target_chat_id"] = target_chat_id
    context.user_data["autopost_interval_minutes"] = interval_minutes
    await flow_state.sync(context, user_id, _clone_id(context), flow="autopost")

    await update.message.reply_text(
        f"{EMOJI_COLORS.get('success', '✅')} Got it — every {interval_minutes} minute(s) into chat `{target_chat_id}`.\n\n"
        f"Now send the message to repeat: plain text, or a photo/video/document/animation with a caption.\n"
        f"Send /cancel to abort.",
        parse_mode="Markdown"
    )


async def handle_autopost_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called from the text/media dispatcher once mode == 'autopost_await_content'."""
    target_chat_id = context.user_data.get("autopost_target_chat_id")
    interval_minutes = context.user_data.get("autopost_interval_minutes")
    admin_id = update.effective_user.id
    msg = update.message

    if target_chat_id is None or interval_minutes is None:
        await flow_state.clear(context, admin_id, _clone_id(context))
        await msg.reply_text("Something went wrong — please run /setrecurring again.")
        return

    content = None
    media_file_id = None
    media_type = None

    if msg.photo:
        media_file_id = msg.photo[-1].file_id
        media_type = "photo"
        content = msg.caption
    elif msg.video:
        media_file_id = msg.video.file_id
        media_type = "video"
        content = msg.caption
    elif msg.animation:
        media_file_id = msg.animation.file_id
        media_type = "animation"
        content = msg.caption
    elif msg.document:
        media_file_id = msg.document.file_id
        media_type = "document"
        content = msg.caption
    elif msg.text:
        content = msg.text
    else:
        await msg.reply_text("Unsupported message type — send text, photo, video, animation, or a document.")
        return

    post_id = await db.create_recurring_post(
        chat_id=target_chat_id,
        admin_id=admin_id,
        interval_minutes=interval_minutes,
        content=content,
        media_file_id=media_file_id,
        media_type=media_type,
    )

    await flow_state.clear(context, admin_id, _clone_id(context))

    await msg.reply_text(
        f"{EMOJI_COLORS.get('success', '✅')} Autopost #{post_id} saved — will post to `{target_chat_id}` "
        f"every {interval_minutes} minute(s).\nUse /stoprecurring {post_id} to stop it, or /listrecurring to see all.",
        parse_mode="Markdown"
    )


async def cmd_stoprecurring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args or []
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("Usage: /stoprecurring <id>  (see /listrecurring for ids)")
        return
    post_id = int(args[0])
    is_owner = user_id == ADMIN_ID
    ok = await db.deactivate_recurring_post(post_id, user_id, is_owner=is_owner)
    if ok:
        await update.message.reply_text(f"{EMOJI_COLORS.get('success', '✅')} Autopost #{post_id} stopped.")
    else:
        await update.message.reply_text("Couldn't stop that — either it doesn't exist or it isn't yours.")


async def cmd_listrecurring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type in ("group", "supergroup", "channel"):
        posts = await db.list_recurring_for_chat(chat.id)
    elif user_id == ADMIN_ID:
        posts = await db.get_all_active_recurring()
    else:
        posts = await db.list_recurring_for_admin(user_id)

    if not posts:
        await update.message.reply_text("No active recurring posts.")
        return

    lines = ["📌 *Active autoposts:*"]
    for p in posts:
        interval = p.get("interval_minutes") or (p.get("interval_hours") or 0) * 60
        preview = (p.get("content") or f"[{p.get('media_type')}]" or "").strip()
        preview = (preview[:40] + "…") if len(preview) > 40 else preview
        lines.append(f"#{p['id']} → chat `{p['chat_id']}` every {interval}m — {preview}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
