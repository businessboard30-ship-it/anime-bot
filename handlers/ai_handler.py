"""
AI Features Handler — AI Chat and Image Generation
Premium tier gated features with daily usage limits
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from modules.ai_features import (
    ai_chat, generate_image, check_ai_usage_limit,
    get_user_ai_usage, AI_USAGE_CAPS
)
from modules.superbot_adapter import get_user_tier
from utils import is_owner
from handlers import utility_paywall
from database import db
from config import ADMIN_ID
from utils import safe_edit_message

def _clone_id(context) -> int:
    """0 for the main bot, else the running clone's id — tier, quota, and
    subscription lookups must be scoped to this so they never leak across
    the main bot and other clones."""
    clone_config = context.bot_data.get("clone_config")
    return clone_config.get("clone_id") if clone_config else 0

logger = logging.getLogger(__name__)


async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ai or /aichat <message> — or bare /ai, which now drops the user into
    waiting mode instead of demanding the old /aichat <msg> syntax.

    Gated by the shared AI Chat + Download paywall (handlers/utility_paywall.py):
    2 free messages, then a 25 GHS / 2-month subscription that also unlocks
    Download. Founders bypass the paywall entirely.
    """
    try:
        user_id = update.effective_user.id

        if not is_owner(user_id, context):
            allowed, _usage = await utility_paywall.check_access(update, context, "ai_chat")
            if not allowed:
                await utility_paywall.send_paywall_message(update, context, "ai_chat")
                return

        # No message yet -> waiting mode instead of a static usage message
        if not context.args or len(context.args) == 0:
            await _enter_ai_waiting_mode(update, context)
            return

        message = " ".join(context.args).strip()

        if not message or len(message) > 1000:
            await update.message.reply_text("Message must be 1-1000 characters.")
            return

        await _run_ai_chat(update, context, message, user_id)

    except Exception as e:
        logger.error(f"[v0] Error in ai_chat_handler: {e}")
        await update.message.reply_text(f"Error: {str(e)[:50]}")


async def _enter_ai_waiting_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Puts the user in 'awaiting_ai_message' mode — their next plain-text
    message goes straight to the AI, no /aichat prefix needed."""
    context.user_data["awaiting_ai_message"] = True
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Exit AI Chat", callback_data="cancel_waiting_mode")]])
    text = (
        "🤖 **AI Chat**\n\n"
        "Send your message now — ask about anime, get recommendations, or chat "
        "about anything. Keep sending messages and I'll keep replying, no need "
        "to tap this again each time.\n\n"
        "Type /cancel or tap below to exit."
    )
    query = update.callback_query
    if query:
        await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def start_ai_chat_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the '🤖 AI Chat' button (callback_data 'tools_ai_info')."""
    user_id = update.effective_user.id
    if not is_owner(user_id, context):
        allowed, _usage = await utility_paywall.check_access(update, context, "ai_chat")
        if not allowed:
            await utility_paywall.send_paywall_message(update, context, "ai_chat")
            return
    await _enter_ai_waiting_mode(update, context)


async def handle_ai_waiting_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routed from handle_message() in api/bot.py when 'awaiting_ai_message'
    is set — the user's plain-text message becomes the AI prompt directly.

    Stays in this mode after replying, so the user can keep chatting without
    re-tapping 'AI Chat' before every message. Mode only ends via /cancel or
    the 'Exit AI Chat' button (handled in api/bot.py)."""
    user_id = update.effective_user.id
    message = (update.message.text or "").strip()

    if not message or len(message) > 1000:
        await update.message.reply_text("Message must be 1-1000 characters. Send another message, or /cancel to exit AI Chat.")
        return

    if not is_owner(user_id, context):
        allowed, _usage = await utility_paywall.check_access(update, context, "ai_chat")
        if not allowed:
            context.user_data.pop("awaiting_ai_message", None)
            await utility_paywall.send_paywall_message(update, context, "ai_chat")
            return

    await _run_ai_chat(update, context, message, user_id)


def _exit_ai_chat_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup | None:
    """Exit button attached to every AI reply while the user is still in
    waiting mode, not just the initial entry message — otherwise there's
    no visible way to leave the chat once you're a few messages in."""
    if context.user_data.get("awaiting_ai_message"):
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Exit AI Chat", callback_data="cancel_waiting_mode")]])
    return None


async def _run_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, user_id: int):
    """Shared tail end for both the /aichat <args> path and the waiting-mode
    path: run the AI, send the reply, then consume a free use if applicable."""
    anime_keywords = ["anime", "manga", "character", "episode", "series", "watch", "recommend"]
    is_anime = any(kw in message.lower() for kw in anime_keywords)

    keyboard = _exit_ai_chat_keyboard(context)

    await update.message.reply_text("🤖 Thinking...")

    response = await ai_chat(user_id, message, is_anime_question=is_anime)

    if not response:
        detail = getattr(ai_chat, "last_error", None)
        if user_id == ADMIN_ID and detail:
            await update.message.reply_text(f"AI service error (admin detail):\n{detail[:500]}", reply_markup=keyboard)
        else:
            await update.message.reply_text("AI service error. Try again later.", reply_markup=keyboard)
        if detail:
            logger.error(f"[v0] AI chat failed for user {user_id}: {detail}")
        return

    if len(response) > 4096:
        response = response[:4090] + "..."

    await update.message.reply_text(response, reply_markup=keyboard)

    if not is_owner(user_id, context):
        await utility_paywall.consume_free_use(user_id, context, "ai_chat")


async def ai_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /aiimage <prompt> [anime|realistic|3d]
    Generate an image from a prompt.
    Gated behind tier system with daily image limits.
    """
    try:
        user = update.effective_user
        user_id = user.id
        owner = is_owner(user_id, context)

        # Get user tier
        tier = await get_user_tier(user_id)
        if tier not in AI_USAGE_CAPS:
            tier = "basic"

        # Check usage limit (founder / clone owner bypass daily caps entirely)
        if not owner:
            allowed, warning_msg = await check_ai_usage_limit(user_id, tier, "images")

            if not allowed:
                await update.message.reply_text(
                    f"❌ {warning_msg}\n\n💎 Upgrade to Pro or Elite tier for more!"
                )
                return

            if warning_msg:
                await update.message.reply_text(warning_msg)
        
        # Parse arguments
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /aiimage <prompt> [anime|realistic|3d]\n"
                "Example: /aiimage a beautiful sunset anime\n\n"
                "Styles: anime (default), realistic, 3d"
            )
            return
        
        # Extract style if provided
        style = "anime"
        if context.args[-1].lower() in ["anime", "realistic", "3d"]:
            style = context.args[-1].lower()
            prompt = " ".join(context.args[:-1])
        else:
            prompt = " ".join(context.args)
        
        if not prompt or len(prompt) > 500:
            await update.message.reply_text("Prompt must be 1-500 characters.")
            return
        
        await update.message.reply_text(f"🎨 Generating {style} image from: {prompt[:50]}...\nThis may take 30-60 seconds...")
        
        # Generate image
        result = await generate_image(user_id, prompt, style)
        
        if "error" in result:
            await update.message.reply_text(f"❌ Error: {result['error']}")
            return
        
        if not result.get("url"):
            await update.message.reply_text("Image generation failed. Try again.")
            return
        
        # Send image
        try:
            await update.message.reply_photo(
                photo=result["url"],
                caption=f"✨ {result.get('prompt', 'Image')[:100]}\nModel: {result.get('model', 'Unknown')}"
            )
        except Exception as e:
            logger.error(f"[v0] Error sending image: {e}")
            await update.message.reply_text(f"Image generated but failed to send: {str(e)[:50]}")
    
    except Exception as e:
        logger.error(f"[v0] Error in ai_image_handler: {e}")
        await update.message.reply_text(f"Error: {str(e)[:50]}")


async def ai_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /aistatus
    Show user's AI usage status: AI Chat free-uses/subscription status
    (handlers/utility_paywall.py) plus the existing daily image-gen cap.
    """
    try:
        user = update.effective_user
        user_id = user.id
        
        # Get tier (still used for /aiimage's daily cap — unaffected by the new paywall)
        tier = await get_user_tier(user_id)
        if tier not in AI_USAGE_CAPS:
            tier = "basic"
        
        images_used = await get_user_ai_usage(user_id, "images")
        caps = AI_USAGE_CAPS[tier]
        image_cap = caps["daily_images"]

        # AI Chat status under the shared AI Chat / Download paywall
        if is_owner(user_id, context):
            ai_chat_line = "💬 AI Chat: unlimited (founder)"
        else:
            usage = await db.get_utility_usage(user_id, clone_id=_clone_id(context))
            if usage.get("utility_sub_status") == "active":
                ai_chat_line = "💬 AI Chat: unlimited (subscribed)"
            else:
                used = usage.get("free_ai_chat_uses", 0) or 0
                remaining = max(0, 2 - used)
                ai_chat_line = f"💬 AI Chat: {remaining} free use(s) left, then 25 GHS/2mo"
        
        # Format response
        response = (
            f"🤖 **AI Usage Status**\n\n"
            f"{ai_chat_line}\n"
            f"🎨 Images: {images_used}/{image_cap} today (Tier: {tier.upper()})\n\n"
            f"Use /ai to chat and /aiimage to generate an image.\n"
            f"Image limits reset daily at midnight UTC."
        )
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"[v0] Error in ai_status_handler: {e}")
        await update.message.reply_text(f"Error: {str(e)[:50]}")
