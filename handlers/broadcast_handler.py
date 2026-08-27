"""
One-off broadcast to users and/or groups.

Restricted to the bot owner (ADMIN_ID) — unlike autopost, this reaches every
known user/group at once, so it isn't delegated to per-group admins.

Flow: /broadcast or the "📢 Broadcast" admin button -> admin sends the content
(text or media) -> bot shows a scope picker (Users / Groups / Both) -> if
groups are involved, bot shows a tap-to-toggle list of every known group so
the admin can exempt specific ones with no typing required -> bot shows a
recipient-count confirm -> on confirm, a broadcast_jobs row + one
broadcast_recipients row per recipient are created, and the first batch is
sent immediately. If there are more recipients left, a "Send Next Batch"
button is shown so the admin decides exactly when the rest goes out —
no cron job, no scheduler, nothing running in the background. Just tap the
button whenever you want the next chunk to go, as many times as it takes.
"""
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import ADMIN_ID, EMOJI_COLORS
from database import db
import flow_state
from modules.broadcast_runner import run_broadcast_batch
from utils import safe_edit_message

logger = logging.getLogger(__name__)


def _progress_keyboard(job_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Send Next Batch", callback_data=f"broadcast_continue_{job_id}")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")],
    ])


def _scope_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 All Users (DM)", callback_data="broadcast_scope_users")],
        [InlineKeyboardButton("👥 All Groups", callback_data="broadcast_scope_groups")],
        [InlineKeyboardButton("🌐 Both", callback_data="broadcast_scope_both")],
        [InlineKeyboardButton("❌ Cancel", callback_data="broadcast_scope_cancel")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")],
    ])


def _exempt_groups_keyboard(groups: list, excluded: set) -> InlineKeyboardMarkup:
    """Tap-to-toggle picker: every known group as its own button, checked
    (included) by default, tap to exempt it — no group ID typing needed."""
    keyboard = []
    for g in groups:
        gid = g["group_id"]
        checked = "☑️" if gid not in excluded else "⬜"
        title = (g.get("chat_title") or f"Group {gid}")[:40]
        keyboard.append([InlineKeyboardButton(f"{checked} {title}", callback_data=f"broadcast_exempt_toggle_{gid}")])
    keyboard.append([InlineKeyboardButton("➡️ Continue", callback_data="broadcast_exempt_done")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="broadcast_exempt_back")])
    return InlineKeyboardMarkup(keyboard)


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Send", callback_data="broadcast_confirm_yes")],
        [InlineKeyboardButton("❌ Cancel", callback_data="broadcast_confirm_no")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")],
    ])


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Broadcast is restricted to the bot owner.")
        return
    context.user_data["mode"] = "broadcast_await_content"
    await flow_state.sync(context, update.effective_user.id, _clone_id(context), flow="broadcast")
    await update.message.reply_text(
        "📢 Send the broadcast content now: plain text, a link, or a photo/video/document/animation with a caption.\n"
        "Send /cancel to abort."
    )


async def start_broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the '📢 Broadcast' admin dashboard button — same flow
    as /broadcast, just reachable in one tap instead of typing a command."""
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Broadcast is restricted to the bot owner.", show_alert=True)
        return
    context.user_data["mode"] = "broadcast_await_content"
    await flow_state.sync(context, update.effective_user.id, _clone_id(context), flow="broadcast")
    await safe_edit_message(query, 
        "📢 Send the broadcast content now: plain text, a link, or a photo/video/document/animation with a caption.\n"
        "Send /cancel to abort, or tap Back below.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]])
    )


async def handle_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called from the text/media dispatcher once mode == 'broadcast_await_content'."""
    msg = update.message
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
        await msg.reply_text("Unsupported message type — send text, a link, photo, video, animation, or a document.")
        return

    context.user_data["broadcast_draft"] = {
        "content": content, "media_file_id": media_file_id, "media_type": media_type
    }
    context.user_data.pop("broadcast_exempt_groups", None)
    context.user_data["mode"] = "broadcast_await_joinlink"
    await flow_state.sync(context, update.effective_user.id, _clone_id(context), flow="broadcast")
    await msg.reply_text(
        "Got it. Want to attach a \"Join Our Group/Channel\" button to this broadcast?\n"
        "Send the invite link (e.g. https://t.me/+xxxxxxxx or https://t.me/yourchannel), "
        "or send /skip to leave it out."
    )


async def handle_broadcast_joinlink_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called from the text dispatcher once mode == 'broadcast_await_joinlink'.
    Admin-assigned per broadcast (not a fixed bot-wide setting) — this is
    separate from the fixed-price Premium Group button, which is attached
    to every broadcast automatically regardless of this link."""
    draft = context.user_data.get("broadcast_draft")
    if not draft:
        await flow_state.clear(context, update.effective_user.id, _clone_id(context))
        await update.message.reply_text("Broadcast cancelled — no draft found. Start over with /broadcast.")
        return

    text = (update.message.text or "").strip()
    if text.lower() in ("/skip", "skip"):
        draft["join_link"] = None
    elif text.startswith("http://") or text.startswith("https://"):
        draft["join_link"] = text
    else:
        await update.message.reply_text(
            "That doesn't look like a link. Send a URL starting with http:// or https://, or send /skip."
        )
        return

    context.user_data["mode"] = "broadcast_await_scope"
    await flow_state.sync(context, update.effective_user.id, _clone_id(context), flow="broadcast")
    await update.message.reply_text("Who should receive this?", reply_markup=_scope_keyboard())


def _clone_id(context) -> int:
    """0 for the main bot, else the running clone's id — every group/channel
    lookup in this file must be scoped to this so a clone's broadcast can
    never reach the main bot's or another clone's groups."""
    clone_config = context.bot_data.get("clone_config")
    return clone_config.get("clone_id") if clone_config else 0


async def _show_confirm(query, context, scope: str):
    excluded = context.user_data.get("broadcast_exempt_groups", set())
    counts = await db.preview_broadcast_counts(scope, excluded_group_ids=list(excluded), clone_id=_clone_id(context))
    context.user_data["mode"] = "broadcast_await_confirm"
    await flow_state.sync(context, query.from_user.id, _clone_id(context), flow="broadcast")
    note = f" ({len(excluded)} group(s) exempted)" if excluded and scope in ("groups", "both") else ""
    draft = context.user_data.get("broadcast_draft") or {}
    join_note = " Includes a Join button." if draft.get("join_link") else ""
    await safe_edit_message(query, 
        f"This will send to *{counts['total']}* recipient(s) "
        f"({counts['users']} users, {counts['groups']} groups){note}.{join_note} Proceed?",
        parse_mode="Markdown",
        reply_markup=_confirm_keyboard()
    )


async def handle_broadcast_scope_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, scope: str):
    query = update.callback_query
    draft = context.user_data.get("broadcast_draft")
    if scope == "cancel" or not draft:
        await flow_state.clear(context, update.effective_user.id, _clone_id(context))
        await safe_edit_message(query, "Broadcast cancelled.")
        return

    context.user_data["broadcast_scope"] = scope

    if scope in ("groups", "both"):
        # Tap-to-exempt step — no group ID typing needed.
        groups = await db.get_known_groups_with_titles(clone_id=_clone_id(context))
        if not groups:
            await _show_confirm(query, context, scope)
            return
        context.user_data["broadcast_exempt_groups"] = set()
        context.user_data["mode"] = "broadcast_await_exempt"
        await flow_state.sync(context, update.effective_user.id, _clone_id(context), flow="broadcast")
        await safe_edit_message(query, 
            "Tap any group to exempt it from this broadcast, then Continue.",
            reply_markup=_exempt_groups_keyboard(groups, set())
        )
        return

    await _show_confirm(query, context, scope)


async def handle_broadcast_exempt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """action is either a group_id (string) to toggle, 'done', or 'back'."""
    query = update.callback_query
    scope = context.user_data.get("broadcast_scope")
    draft = context.user_data.get("broadcast_draft")
    if not scope or not draft:
        await safe_edit_message(query, "Broadcast cancelled.")
        return

    if action == "back":
        context.user_data.pop("broadcast_exempt_groups", None)
        context.user_data["mode"] = "broadcast_await_scope"
        await flow_state.sync(context, update.effective_user.id, _clone_id(context), flow="broadcast")
        await safe_edit_message(query, "Who should receive this?", reply_markup=_scope_keyboard())
        return

    if action == "done":
        await _show_confirm(query, context, scope)
        return

    # Toggle this group_id in/out of the exempt set
    try:
        gid = int(action)
    except ValueError:
        return
    excluded = context.user_data.setdefault("broadcast_exempt_groups", set())
    if gid in excluded:
        excluded.discard(gid)
    else:
        excluded.add(gid)
    await flow_state.sync(context, update.effective_user.id, _clone_id(context), flow="broadcast")

    groups = await db.get_known_groups_with_titles(clone_id=_clone_id(context))
    await safe_edit_message(query, 
        "Tap any group to exempt it from this broadcast, then Continue.",
        reply_markup=_exempt_groups_keyboard(groups, excluded)
    )


async def handle_broadcast_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, confirmed: bool):
    query = update.callback_query
    admin_id = update.effective_user.id
    draft = context.user_data.get("broadcast_draft")
    scope = context.user_data.get("broadcast_scope")
    excluded = context.user_data.get("broadcast_exempt_groups", set())

    context.user_data.pop("mode", None)
    context.user_data.pop("broadcast_draft", None)
    context.user_data.pop("broadcast_scope", None)
    context.user_data.pop("broadcast_exempt_groups", None)
    await flow_state.clear(context, admin_id, _clone_id(context))

    if not confirmed or not draft or not scope:
        await safe_edit_message(query, "Broadcast cancelled.")
        return

    job = await db.create_broadcast_job(
        admin_id=admin_id,
        target_scope=scope,
        content=draft.get("content"),
        media_file_id=draft.get("media_file_id"),
        media_type=draft.get("media_type"),
        excluded_group_ids=list(excluded),
        join_link=draft.get("join_link"),
        clone_id=_clone_id(context),
    )

    await safe_edit_message(query, 
        f"{EMOJI_COLORS.get('success', '✅')} Broadcast #{job['id']} queued for {job['total_recipients']} recipient(s). Sending first batch..."
    )

    result = await run_broadcast_batch(context.bot, job_id=job["id"])
    await _report_batch_progress(query, job["id"], result)


async def handle_broadcast_continue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, job_id: int):
    """Callback for the manually-tapped '▶️ Send Next Batch' button — sends
    one more batch of the given job right now. No cron, no scheduler; the
    admin controls the pace entirely by tapping this whenever they want."""
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Broadcast is restricted to the bot owner.", show_alert=True)
        return

    await query.answer("Sending next batch...")
    result = await run_broadcast_batch(context.bot, job_id=job_id)
    await _report_batch_progress(query, job_id, result)


async def _report_batch_progress(query, job_id: int, result: dict):
    status = result.get("job_status")
    sent = result.get("sent", 0)
    failed = result.get("failed", 0)

    if status == "none_pending":
        await safe_edit_message(query, f"{EMOJI_COLORS.get('success', '✅')} Broadcast #{job_id}: nothing left to send.")
        return

    job = await db.get_broadcast_job(job_id)
    total = job.get("total_recipients", 0) if job else 0
    done_count = (job.get("sent_count", 0) + job.get("failed_count", 0)) if job else 0

    if status == "done":
        await safe_edit_message(query, 
            f"{EMOJI_COLORS.get('success', '✅')} Broadcast #{job_id} complete: "
            f"{job.get('sent_count', 0)} sent, {job.get('failed_count', 0)} failed, out of {total}."
        )
    else:
        await safe_edit_message(query, 
            f"Broadcast #{job_id}: {done_count}/{total} processed so far "
            f"(+{sent} sent, +{failed} failed this batch). Tap below to send the next batch whenever you're ready.",
            reply_markup=_progress_keyboard(job_id)
        )
