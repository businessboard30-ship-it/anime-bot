"""
Bot Manager Handlers
BotFather-style management UI for bots the user already owns.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import EMOJI_COLORS
import flow_state
from modules import bot_manager
from utils import safe_edit_message


def _bots_keyboard(bots: list) -> InlineKeyboardMarkup:
    rows = []
    for b in bots:
        rows.append([InlineKeyboardButton(f"🤖 @{b['username']}", callback_data=f"bot_view_{b['id']}")])
    rows.append([InlineKeyboardButton("➕ ADD A BOT", callback_data="bot_add")])
    rows.append([InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def _bot_detail_keyboard(bot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ SET NAME", callback_data=f"bot_setname_{bot_id}")],
        [InlineKeyboardButton("📝 SET DESCRIPTION", callback_data=f"bot_setdesc_{bot_id}")],
        [InlineKeyboardButton("⚙️ SET COMMANDS", callback_data=f"bot_setcmds_{bot_id}")],
        [InlineKeyboardButton("🔄 REFRESH INFO", callback_data=f"bot_view_{bot_id}")],
        [InlineKeyboardButton("🗑️ REMOVE BOT", callback_data=f"bot_remove_{bot_id}")],
        [InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_bots")],
    ])


async def show_bot_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Bot Manager menu (m_bots or /botmanager)"""
    query = update.callback_query
    user_id = update.effective_user.id
    bots = await bot_manager.get_user_bots(user_id)

    text = (
        f"🛠️ **BOT MANAGER**\n\n"
        f"Manage bots you already created with @BotFather.\n"
        f"You have **{len(bots)}** bot(s) registered here.\n\n"
        f"_Tap a bot to edit its name, description or commands — "
        f"or add a new one below._"
    )
    if query:
        await safe_edit_message(query, text, reply_markup=_bots_keyboard(bots), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=_bots_keyboard(bots), parse_mode="Markdown")


async def start_add_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for a bot token to register (bot_add)"""
    query = update.callback_query
    context.user_data["mode"] = "addbot"
    await flow_state.sync(context, update.effective_user.id, 0, flow="bot_manager")
    await safe_edit_message(query, 
        "➕ **ADD A BOT**\n\n"
        "Get a token from @BotFather, then paste it here.\n"
        "It looks like:\n`123456789:AAExampleTokenString`\n\n"
        "_I never share your token with anyone else._",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_bots")
        ]]),
        parse_mode="Markdown"
    )


async def handle_add_bot_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a pasted bot token (mode == 'addbot'), called from the main text dispatcher"""
    user_id = update.effective_user.id
    token = update.message.text.strip()

    await update.message.reply_text("🔍 _Checking token…_", parse_mode="Markdown")
    ok, info = await bot_manager.verify_bot_token(token)
    if not ok:
        await update.message.reply_text(
            f"⚠️ That token didn't work: {info}\nDouble-check it and send it again."
        )
        return

    context.user_data.pop("mode", None)
    await flow_state.clear(context, user_id, 0)
    added = await bot_manager.add_managed_bot(user_id, token, info)
    bots = await bot_manager.get_user_bots(user_id)

    if added:
        await update.message.reply_text(
            f"✅ *@{info.get('username')}* added to BotManager!",
            parse_mode="Markdown",
            reply_markup=_bots_keyboard(bots)
        )
    else:
        await update.message.reply_text(
            "ℹ️ That bot is already registered here.",
            reply_markup=_bots_keyboard(bots)
        )


async def show_bot_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show live details for one managed bot (bot_view_<id>)"""
    query = update.callback_query
    user_id = update.effective_user.id
    bot_id = int(query.data.split("_")[-1])

    record = await bot_manager.get_managed_bot(user_id, bot_id)
    if not record:
        bots = await bot_manager.get_user_bots(user_id)
        await safe_edit_message(query, "⚠️ Bot not found.", reply_markup=_bots_keyboard(bots))
        return

    ok, info = await bot_manager.verify_bot_token(record["token"])
    if not ok:
        bots = await bot_manager.get_user_bots(user_id)
        await safe_edit_message(query, f"⚠️ Couldn't reach this bot: {info}", reply_markup=_bots_keyboard(bots))
        return

    await safe_edit_message(query, 
        f"🤖 **@{info.get('username')}**\n\n"
        f"📛 Name: **{info.get('first_name')}**\n"
        f"🆔 Bot ID: `{info.get('id')}`\n"
        f"🔗 Can join groups: {'✅' if info.get('can_join_groups') else '❌'}\n"
        f"💬 Can read all messages: {'✅' if info.get('can_read_all_group_messages') else '❌'}",
        reply_markup=_bot_detail_keyboard(bot_id),
        parse_mode="Markdown"
    )


async def start_set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for a new bot name (bot_setname_<id>)"""
    query = update.callback_query
    bot_id = int(query.data.split("_")[-1])
    context.user_data["mode"] = f"botmgr_setname_{bot_id}"
    await flow_state.sync(context, update.effective_user.id, 0, flow="bot_manager")
    await safe_edit_message(query, 
        "✏️ Send the **new name** for this bot:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data=f"bot_view_{bot_id}")
        ]]),
        parse_mode="Markdown"
    )


async def start_set_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for a new bot description (bot_setdesc_<id>)"""
    query = update.callback_query
    bot_id = int(query.data.split("_")[-1])
    context.user_data["mode"] = f"botmgr_setdesc_{bot_id}"
    await flow_state.sync(context, update.effective_user.id, 0, flow="bot_manager")
    await safe_edit_message(query, 
        "📝 Send the **new description** (shown on the bot's profile page):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data=f"bot_view_{bot_id}")
        ]]),
        parse_mode="Markdown"
    )


async def start_set_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for a new command list (bot_setcmds_<id>)"""
    query = update.callback_query
    bot_id = int(query.data.split("_")[-1])
    context.user_data["mode"] = f"botmgr_setcmds_{bot_id}"
    await flow_state.sync(context, update.effective_user.id, 0, flow="bot_manager")
    await safe_edit_message(query, 
        "⚙️ Send the **command list**, one per line, like:\n"
        "`start - Start the bot`\n`help - Show help`",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data=f"bot_view_{bot_id}")
        ]]),
        parse_mode="Markdown"
    )


async def handle_setname_message(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int):
    """Handle the typed new name (mode == 'botmgr_setname_<id>')"""
    user_id = update.effective_user.id
    text = update.message.text
    context.user_data.pop("mode", None)
    await flow_state.clear(context, user_id, 0)

    record = await bot_manager.get_managed_bot(user_id, bot_id)
    if not record:
        await update.message.reply_text(f"{EMOJI_COLORS.get('error', '❌')} Bot not found.")
        return

    r = await bot_manager.tg_call(record["token"], "setMyName", {"name": text[:64]})
    if r.get("ok"):
        await update.message.reply_text("✅ Name updated!", reply_markup=_bot_detail_keyboard(bot_id))
    else:
        await update.message.reply_text(f"⚠️ Failed: {r.get('description')}", reply_markup=_bot_detail_keyboard(bot_id))


async def handle_setdesc_message(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int):
    """Handle the typed new description (mode == 'botmgr_setdesc_<id>')"""
    user_id = update.effective_user.id
    text = update.message.text
    context.user_data.pop("mode", None)
    await flow_state.clear(context, user_id, 0)

    record = await bot_manager.get_managed_bot(user_id, bot_id)
    if not record:
        await update.message.reply_text(f"{EMOJI_COLORS.get('error', '❌')} Bot not found.")
        return

    r = await bot_manager.tg_call(record["token"], "setMyDescription", {"description": text[:512]})
    if r.get("ok"):
        await update.message.reply_text("✅ Description updated!", reply_markup=_bot_detail_keyboard(bot_id))
    else:
        await update.message.reply_text(f"⚠️ Failed: {r.get('description')}", reply_markup=_bot_detail_keyboard(bot_id))


async def handle_setcmds_message(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int):
    """Handle the typed command list (mode == 'botmgr_setcmds_<id>')"""
    user_id = update.effective_user.id
    text = update.message.text

    record = await bot_manager.get_managed_bot(user_id, bot_id)
    if not record:
        context.user_data.pop("mode", None)
        await flow_state.clear(context, user_id, 0)
        await update.message.reply_text(f"{EMOJI_COLORS.get('error', '❌')} Bot not found.")
        return

    cmds = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "-" in line:
            cmd, desc = line.split("-", 1)
            cmds.append({"command": cmd.strip().lstrip("/")[:32], "description": desc.strip()[:256]})

    if not cmds:
        await update.message.reply_text(
            "⚠️ I couldn't parse that. Use one per line: `start - Start the bot`",
            parse_mode="Markdown"
        )
        return

    context.user_data.pop("mode", None)
    await flow_state.clear(context, user_id, 0)
    r = await bot_manager.tg_call(record["token"], "setMyCommands", {"commands": cmds})
    if r.get("ok"):
        await update.message.reply_text(f"✅ {len(cmds)} command(s) updated!", reply_markup=_bot_detail_keyboard(bot_id))
    else:
        await update.message.reply_text(f"⚠️ Failed: {r.get('description')}", reply_markup=_bot_detail_keyboard(bot_id))


async def start_remove_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for confirmation before removing a bot (bot_remove_<id>)"""
    query = update.callback_query
    bot_id = int(query.data.split("_")[-1])
    await safe_edit_message(query, 
        "⚠️ **Remove this bot from BotManager?**\n"
        "_This only removes it from here — the bot itself keeps running._",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ YES, REMOVE", callback_data=f"bot_remove_confirm_{bot_id}"),
            InlineKeyboardButton("❌ CANCEL", callback_data=f"bot_view_{bot_id}"),
        ]]),
        parse_mode="Markdown"
    )


async def confirm_remove_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actually remove the bot (bot_remove_confirm_<id>)"""
    query = update.callback_query
    user_id = update.effective_user.id
    bot_id = int(query.data.split("_")[-1])

    await bot_manager.remove_managed_bot(user_id, bot_id)
    bots = await bot_manager.get_user_bots(user_id)
    await safe_edit_message(query, "🗑️ Bot removed from BotManager.", reply_markup=_bots_keyboard(bots))
