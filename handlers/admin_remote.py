"""
Admin Panel — Remote Group/Channel Control.

Lets the bot admin pick any group/channel the bot is a member of (from a
list — no need to open the chat) and run group-moderation commands against
it directly from a DM. Every command in handlers/moderation.py was written
assuming update.effective_chat / update.message belong to the group itself;
rather than rewrite all 31 of them individually, this module builds a thin
proxy Update that points effective_chat at the chosen remote chat and routes
message.reply_text() into that chat (so /rules, /warn, etc. have the exact
same visible effect as if they'd been typed in-group), while keeping
effective_user as the real admin so the existing admin-permission checks
inside moderation.py (_is_group_admin / _require_admin) still verify the
admin is actually an admin of that specific chat.

Two commands are intentionally NOT exposed here: /del and /pin. Both work by
deleting/pinning "the message this is a reply to" — a message that only
exists inside the group itself, so there is nothing to reply to from a DM.
Those stay in-group-only.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database import db
from keyboards import keyboard_gen
from config import ADMIN_ID
from handlers import moderation
from utils import safe_edit_message

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "member": "👤 Member Actions",
    "filters": "🚫 Filters & Words",
    "settings": "⚙️ Mod Settings",
    "custom": "💬 Custom Commands",
    "content": "📋 Content & Info",
}

# name -> (function, target_type, usage_hint, category)
# target_type: "none" (runs immediately, no args) / "user_id" (needs a numeric
# Telegram user id as the first token, no reply-to-message available in a DM)
# / "raw" (free-text args, same as typing them after the command in-group)
REMOTE_COMMANDS = {
    "warn":               (moderation.warn_command,               "user_id", "<user_id> [reason]", "member"),
    "unwarn":             (moderation.unwarn_command,              "user_id", "<user_id>", "member"),
    "warns":              (moderation.warns_command,               "user_id", "<user_id>", "member"),
    "ban":                (moderation.ban_command,                 "user_id", "<user_id> [reason]", "member"),
    "unban":              (moderation.unban_command,               "raw",     "<user_id>", "member"),
    "kick":               (moderation.kick_command,                "user_id", "<user_id>", "member"),
    "mute":               (moderation.mute_command,                "user_id", "<user_id> [minutes]", "member"),
    "unmute":             (moderation.unmute_command,               "user_id", "<user_id>", "member"),

    "filter":             (moderation.filter_add_command,          "raw",  "<word or phrase>", "filters"),
    "unfilter":           (moderation.filter_remove_command,       "raw",  "<word or phrase>", "filters"),
    "filters":            (moderation.filter_list_command,         "none", "", "filters"),

    "modsettings":        (moderation.modsettings_command,         "raw",  "<setting> <on|off> — or blank for current settings", "settings"),
    "setgate":            (moderation.setgate_command,             "raw",  "<link> [label]", "settings"),
    "gate":               (moderation.gate_toggle_command,         "raw",  "on|off", "settings"),
    "whitelistdomain":    (moderation.whitelistdomain_command,     "raw",  "<domain>", "settings"),
    "unwhitelistdomain":  (moderation.unwhitelistdomain_command,   "raw",  "<domain>", "settings"),
    "listwhitelist":      (moderation.listwhitelist_command,       "none", "", "settings"),
    "setspamrules":       (moderation.setspamrules_command,        "raw",  "<dup_count> <flood_count> <window_seconds>", "settings"),
    "setautomute":        (moderation.setautomute_command,         "raw",  "<minutes>", "settings"),
    "setwarnlimit":       (moderation.setwarnlimit_command,        "raw",  "<N>", "settings"),
    "setpintag":          (moderation.setpintag_command,           "raw",  "<tag>", "settings"),
    "setjoinlink":        (moderation.setjoinlink_command,         "none", "", "settings"),

    "setcmd":             (moderation.setcmd_command,              "raw",  "<name> <response text>", "custom"),
    "delcmd":             (moderation.delcmd_command,              "raw",  "<name>", "custom"),
    "listcmds":           (moderation.listcmds_command,            "none", "", "custom"),

    "rules":              (moderation.rules_command,               "none", "", "content"),
    "groupstats":         (moderation.stats_command,                "none", "", "content"),
    "setwelcome":         (moderation.setwelcome_command,          "raw",  "<message, use {name} as a placeholder>", "content"),
    "setpaybutton":       (moderation.setpaybutton_command,        "raw",  "<Label> | <amount in GHS>", "content"),
    "removepaybutton":    (moderation.removepaybutton_command,     "none", "", "content"),
    "logs":               (moderation.logs_command,                "none", "", "content"),
}


class _RemoteChat:
    def __init__(self, chat_id: int, chat_type: str, title: str = None):
        self.id = chat_id
        self.type = chat_type
        self.title = title


class _RemoteMessage:
    """Stands in for update.message. reply_text() sends INTO the target
    chat (matching what running the command in-group would do); the admin
    gets a separate short confirmation in their DM after the call returns."""
    def __init__(self, bot, chat_id: int, text: str):
        self._bot = bot
        self.chat_id = chat_id
        self.text = text
        self.reply_to_message = None

    async def reply_text(self, text, **kwargs):
        return await self._bot.send_message(chat_id=self.chat_id, text=text, **kwargs)

    async def delete(self):
        return None


class _RemoteUpdate:
    """Wraps the admin's real DM Update so unmodified moderation.py command
    functions can run against a chat the admin isn't currently inside."""
    def __init__(self, real_update: Update, bot, chat_id: int, chat_type: str, text: str,
                 remote_target=None, chat_title: str = None):
        self._real = real_update
        self.effective_chat = _RemoteChat(chat_id, chat_type, chat_title)
        self.effective_user = real_update.effective_user
        self.message = _RemoteMessage(bot, chat_id, text)
        self.callback_query = None
        if remote_target:
            self._remote_target = remote_target

    def __getattr__(self, name):
        return getattr(self._real, name)


async def show_admin_group_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        if query:
            await query.answer("Unauthorized", show_alert=True)
        return

    clone_config = context.bot_data.get("clone_config")
    clone_id = clone_config.get("clone_id") if clone_config else 0
    chats = await db.list_bot_chats(clone_id=clone_id)
    context.user_data["admin_chat_cache"] = chats

    if not chats:
        text = "📋 **Manage Groups/Channels**\n\nI'm not in any groups or channels yet."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]])
    else:
        text = f"📋 **Manage Groups/Channels** ({len(chats)})\n\nPick one to run commands on it remotely:"
        keyboard = keyboard_gen.admin_group_list_keyboard(chats, page)

    if query:
        await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def handle_admin_grouplist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Unauthorized", show_alert=True)
        return
    page = int(query.data.rsplit("_", 1)[1])
    await show_admin_group_list(update, context, page)


async def select_target_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    chat_id = int(query.data[len("admin_target_"):])
    clone_config = context.bot_data.get("clone_config")
    clone_id = clone_config.get("clone_id") if clone_config else 0
    chats = context.user_data.get("admin_chat_cache") or await db.list_bot_chats(clone_id=clone_id)
    match = next((c for c in chats if c["chat_id"] == chat_id), None)

    title = match.get("chat_title") if match else None
    chat_type = match.get("chat_type") if match else "supergroup"
    context.user_data["admin_target_chat"] = {"id": chat_id, "type": chat_type or "supergroup", "title": title}

    await safe_edit_message(query, 
        f"🎯 **Target:** {title or chat_id}\n\nPick a category:",
        reply_markup=keyboard_gen.admin_remote_categories_keyboard(chat_id),
        parse_mode="Markdown"
    )


async def show_category_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    prefix, chat_id_str = query.data.rsplit("_", 1)
    category = prefix[len("admin_cat_"):]
    chat_id = int(chat_id_str)

    commands = [{"name": name} for name, spec in REMOTE_COMMANDS.items() if spec[3] == category]
    label = CATEGORY_LABELS.get(category, category)

    await safe_edit_message(query, 
        f"{label}\n\nTap a command to run it on this chat:",
        reply_markup=keyboard_gen.admin_remote_command_list_keyboard(chat_id, category, commands),
        parse_mode="Markdown"
    )


async def handle_admin_run_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tapping a command: run immediately if it needs no args, otherwise
    enter waiting mode for the admin's next DM message."""
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    prefix, chat_id_str = query.data.rsplit("_", 1)
    cmd_name = prefix[len("admin_run_"):]
    chat_id = int(chat_id_str)

    spec = REMOTE_COMMANDS.get(cmd_name)
    if not spec:
        await query.answer("Unknown command.", show_alert=True)
        return

    target_chat = context.user_data.get("admin_target_chat") or {}
    if target_chat.get("id") != chat_id:
        target_chat = {"id": chat_id, "type": "supergroup", "title": None}

    _, target_type, usage_hint, _ = spec

    if target_type == "none":
        await query.answer("Running…")
        await _dispatch(update, context, cmd_name, chat_id, target_chat.get("type"),
                         target_chat.get("title"), raw_text="")
        return

    context.user_data["admin_remote_cmd"] = cmd_name
    context.user_data["admin_remote_chat"] = target_chat
    hint = f"Usage: {usage_hint}" if usage_hint else ""
    await safe_edit_message(query, 
        f"⌨️ Send the arguments for **/{cmd_name}** on **{target_chat.get('title') or chat_id}** now.\n{hint}\n\n"
        f"Send /cancel to back out.",
        parse_mode="Markdown"
    )


async def handle_admin_remote_command_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routed from handle_message() in api/bot.py when 'admin_remote_cmd' is
    set — the admin's next plain-text DM becomes the command's arguments."""
    cmd_name = context.user_data.pop("admin_remote_cmd", None)
    target_chat = context.user_data.pop("admin_remote_chat", {}) or {}
    if not cmd_name:
        return

    text = (update.message.text or "").strip()
    if text == "/cancel":
        await update.message.reply_text("Cancelled.")
        return

    await _dispatch(update, context, cmd_name, target_chat.get("id"), target_chat.get("type"),
                     target_chat.get("title"), raw_text=text)


async def _dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE, cmd_name: str,
                     chat_id: int, chat_type: str, chat_title: str, raw_text: str):
    spec = REMOTE_COMMANDS.get(cmd_name)
    if not spec or chat_id is None:
        await update.effective_message.reply_text("⚠️ Lost track of the target chat — start over from the admin panel.")
        return

    func, target_type, _usage_hint, _category = spec
    label = chat_title or str(chat_id)

    remote_target = None
    args_list = []
    command_text = f"/{cmd_name}"

    if target_type == "user_id":
        parts = raw_text.split(maxsplit=1)
        if not parts or not parts[0].lstrip("-").isdigit():
            await update.effective_message.reply_text(
                f"⚠️ First argument must be a numeric Telegram user id for /{cmd_name}. Try again."
            )
            return
        target_id = int(parts[0])
        rest = parts[1] if len(parts) > 1 else ""
        try:
            member = await context.bot.get_chat_member(chat_id, target_id)
            target_name = member.user.first_name or member.user.username or str(target_id)
        except Exception:
            target_name = str(target_id)
        remote_target = (target_id, target_name)
        args_list = rest.split() if rest else []
        command_text = f"/{cmd_name} {rest}".rstrip()
    else:
        args_list = raw_text.split() if raw_text else []
        command_text = f"/{cmd_name} {raw_text}".rstrip() if raw_text else f"/{cmd_name}"

    remote_update = _RemoteUpdate(
        update, context.bot, chat_id, chat_type or "supergroup", command_text,
        remote_target=remote_target, chat_title=chat_title
    )

    saved_args = getattr(context, "args", None)
    context.args = args_list
    try:
        await func(remote_update, context)
        await update.effective_message.reply_text(f"✅ Ran /{cmd_name} on {label}.")
    except Exception as e:
        logger.error(f"[v0] Remote command /{cmd_name} on {chat_id} failed: {e}")
        await update.effective_message.reply_text(f"⚠️ /{cmd_name} on {label} failed: {str(e)[:200]}")
    finally:
        context.args = saved_args
