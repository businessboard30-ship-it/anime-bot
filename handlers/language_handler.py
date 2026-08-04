"""
/language command — lets a user pick their preferred language.

Saved on the user row (users.language) and used two ways elsewhere:
- Static UI strings (menus, disclaimers, errors) are looked up via
  i18n.t(key, lang) wherever a handler has been updated to use it.
- AI-generated content (groq_service.py) is steered via
  i18n.language_instruction(lang) appended to the prompt.

Only a handful of strings have been migrated to i18n.t() so far (see
i18n.py's module docstring) — this is the entry point for that rollout,
not a claim that the whole bot is translated yet.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database import db
from keyboards import keyboard_gen
from i18n import t, SUPPORTED_LANGUAGES

def _clone_id(context) -> int:
    """0 for the main bot, else the running clone's id — tier, quota, and
    subscription lookups must be scoped to this so they never leak across
    the main bot and other clones."""
    clone_config = context.bot_data.get("clone_config")
    return clone_config.get("clone_id") if clone_config else 0

logger = logging.getLogger(__name__)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/language — show the language picker."""
    user_id = update.effective_user.id
    current = await db.get_user_language(user_id, clone_id=_clone_id(context))
    await update.message.reply_text(
        t("choose_language", current),
        reply_markup=keyboard_gen.language_menu()
    )


async def show_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the '🌐 Language' button (callback_data 'tools_language_info')."""
    query = update.callback_query
    user_id = update.effective_user.id
    current = await db.get_user_language(user_id, clone_id=_clone_id(context))
    await query.edit_message_text(
        t("choose_language", current),
        reply_markup=keyboard_gen.language_menu()
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callback_data == 'lang_set_<code>' from the picker."""
    query = update.callback_query
    user_id = update.effective_user.id

    code = query.data.replace("lang_set_", "", 1)
    if code not in SUPPORTED_LANGUAGES:
        await query.answer("Unsupported language.", show_alert=True)
        return

    await db.set_user_language(user_id, code, clone_id=_clone_id(context))
    await query.answer()
    await query.edit_message_text(
        t("language_changed", code, lang_name=SUPPORTED_LANGUAGES[code])
    )
