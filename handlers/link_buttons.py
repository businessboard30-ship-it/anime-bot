"""
Generic labeled-link button builder (feature #8).

Reusable pattern: an admin picks any label ("Join Our Channel", "Rules",
"Support", "Pay Now"...), the bot asks for a URL, saves label->URL per
group in custom_link_buttons, and it becomes a tappable URL button shown
in that group's Group Tools menu. No new code needed per label.

Admin flow (run the command IN the target group, same convention as
/setwelcome, /warn, etc.):
    /addlinkbutton <Label>        -> bot replies "send me the link for '<Label>'"
                                      and puts the admin in a waiting state
    <admin pastes a URL>          -> saved, confirmed
    /listlinkbuttons              -> lists configured buttons with a Remove button each
    /removelinkbutton <Label>     -> removes one directly by label

State uses context.user_data["awaiting_link_button_url"], matching the
context.user_data waiting-state pattern used elsewhere (clone_step,
awaiting_ai_message, etc.).
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import db
from handlers.moderation import _require_admin, _require_group

logger = logging.getLogger(__name__)

URL_PREFIXES = ("http://", "https://", "t.me/", "https://t.me/")


async def addlinkbutton_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/addlinkbutton <Label>"""
    if not await _require_group(update):
        return
    if not await _require_admin(update, context):
        return
    label = update.message.text.partition(" ")[2].strip()
    if not label:
        await update.message.reply_text(
            "Usage: `/addlinkbutton Join Our Channel`\n"
            "I'll then ask you to send the link to attach to it.",
            parse_mode="Markdown"
        )
        return
    context.user_data["awaiting_link_button_url"] = {
        "chat_id": update.effective_chat.id,
        "label": label,
    }
    await update.message.reply_text(
        f"🔗 Send me the link you want to attach to \"{label}\" (or /cancel)."
    )


async def handle_link_button_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MessageHandler callback while awaiting_link_button_url is set."""
    state = context.user_data.get("awaiting_link_button_url")
    text = (update.message.text or "").strip()

    if text.lower() == "/cancel":
        context.user_data.pop("awaiting_link_button_url", None)
        await update.message.reply_text("Cancelled.")
        return

    if not text.startswith(("http://", "https://")):
        await update.message.reply_text(
            "That doesn't look like a link. Please send a URL starting with "
            "http:// or https:// (or /cancel)."
        )
        return

    ok = await db.add_link_button(state["chat_id"], state["label"], text, update.effective_user.id)
    context.user_data.pop("awaiting_link_button_url", None)
    if ok:
        await update.message.reply_text(f"✅ \"{state['label']}\" button saved — it'll show in Group Tools.")
    else:
        await update.message.reply_text("⚠️ Failed to save. Try again.")


async def listlinkbuttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/listlinkbuttons"""
    if not await _require_group(update):
        return
    if not await _require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    buttons = await db.list_link_buttons(chat_id)
    if not buttons:
        await update.message.reply_text(
            "No custom link buttons yet. Add one with `/addlinkbutton <Label>`.",
            parse_mode="Markdown"
        )
        return
    keyboard = [
        [InlineKeyboardButton(f"🗑️ Remove \"{b['label']}\"", callback_data=f"rmlinkbtn_{chat_id}_{b['label']}")]
        for b in buttons
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="grouptools_settings")])
    lines = "\n".join(f"• **{b['label']}** → {b['url']}" for b in buttons)
    await update.message.reply_text(
        f"🔗 **Custom Link Buttons**\n\n{lines}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def removelinkbutton_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/removelinkbutton <Label>"""
    if not await _require_group(update):
        return
    if not await _require_admin(update, context):
        return
    label = update.message.text.partition(" ")[2].strip()
    if not label:
        await update.message.reply_text("Usage: `/removelinkbutton Join Our Channel`", parse_mode="Markdown")
        return
    ok = await db.remove_link_button(update.effective_chat.id, label)
    if ok:
        await update.message.reply_text(f"✅ Removed \"{label}\".")
    else:
        await update.message.reply_text(f"⚠️ No button named \"{label}\" found.")


async def handle_remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """callback_data == 'rmlinkbtn_<chat_id>_<label>'"""
    query = update.callback_query
    _, chat_id_str, label = query.data.split("_", 2)
    ok = await db.remove_link_button(int(chat_id_str), label)
    if ok:
        await query.answer(f"Removed \"{label}\"")
        buttons = await db.list_link_buttons(int(chat_id_str))
        if buttons:
            keyboard = [
                [InlineKeyboardButton(f"🗑️ Remove \"{b['label']}\"", callback_data=f"rmlinkbtn_{chat_id_str}_{b['label']}")]
                for b in buttons
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="grouptools_settings")])
            lines = "\n".join(f"• **{b['label']}** → {b['url']}" for b in buttons)
            await query.edit_message_text(
                f"🔗 **Custom Link Buttons**\n\n{lines}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "No custom link buttons left.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="grouptools_settings")]])
            )
    else:
        await query.answer("Not found.", show_alert=True)


async def get_link_button_rows(chat_id: int):
    """Returns a list of single-button rows (InlineKeyboardButton with url=)
    for this chat's configured custom link buttons, for embedding into
    another menu (e.g. Group Tools)."""
    buttons = await db.list_link_buttons(chat_id)
    return [[InlineKeyboardButton(f"🔗 {b['label']}", url=b["url"])] for b in buttons]
