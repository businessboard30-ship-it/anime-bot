import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import db

logger = logging.getLogger(__name__)
from keyboards import keyboard_gen
from config import EMOJI_COLORS, ADMIN_ID
from utils.rate_limiter import rate_limiter

async def start_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start anime submission workflow - show disclaimer first"""
    query = update.callback_query
    
    # Mark that we're in submission flow
    context.user_data["submission_flow"] = True
    
    # Show disclaimer
    keyboard = [
        [
            InlineKeyboardButton("✅ I Agree", callback_data="accept_submission_disclaimer"),
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
        ]
    ]
    
    disclaimer_text = """
⚖️ **SUBMISSION AGREEMENT**

By submitting content, you confirm:

✓ You have the right to submit this content
✓ The information provided is factually accurate
✓ You're not violating any copyright laws
✓ You own or have permission for any links/images

⚠️ **CONTENT WARNING**

This anime/movie may contain:
• Violence, blood, or gore
• Sexual or suggestive content
• Profanity or strong language
• Psychological themes

By clicking ✅ I AGREE, you accept these terms.
"""
    
    if query:
        await query.edit_message_text(
            disclaimer_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            disclaimer_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def handle_submission_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle submission steps"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if context.user_data.get("submission_step") == "awaiting_name":
        context.user_data["anime_name"] = text
        context.user_data["submission_step"] = "awaiting_episodes"
        
        await update.message.reply_text(
            f"{EMOJI_COLORS['submit']} How many episodes?\n\n(Enter number or 'Unknown')"
        )
    
    elif context.user_data.get("submission_step") == "awaiting_episodes":
        context.user_data["episodes"] = text
        context.user_data["submission_step"] = "awaiting_genres"
        
        await update.message.reply_text(
            f"{EMOJI_COLORS['submit']} Genres? (comma separated)\n\n(e.g. Action, Adventure, Drama)"
        )
    
    elif context.user_data.get("submission_step") == "awaiting_genres":
        context.user_data["genres"] = text
        context.user_data["submission_step"] = "awaiting_synopsis"
        
        await update.message.reply_text(
            f"{EMOJI_COLORS['submit']} Brief description/synopsis:"
        )
    
    elif context.user_data.get("submission_step") == "awaiting_synopsis":
        context.user_data["synopsis"] = text
        
        # Rate limit: check before submitting (Issue 1.3)
        if not await rate_limiter.check_submission_limit(user_id):
            await update.message.reply_text(
                f"{EMOJI_COLORS['error']} You've reached your submission limit for today. "
                f"Try again tomorrow."
            )
            context.user_data["submission_step"] = None
            context.user_data.pop("anime_name", None)
            context.user_data.pop("episodes", None)
            context.user_data.pop("genres", None)
            context.user_data.pop("synopsis", None)
            return
        
        # Submit to database
        await db.add_submission(
            user_id,
            context.user_data.get("anime_name"),
            context.user_data.get("episodes"),
            context.user_data.get("genres"),
            context.user_data.get("synopsis"),
            ""  # image_url - can be added later
        )
        
        await update.message.reply_text(
            f"{EMOJI_COLORS['success']} **Submission Received!**\n\n"
            f"Thank you for contributing! Your submission has been sent for admin review.\n"
            f"You'll be notified when it's approved.",
            reply_markup=keyboard_gen.main_menu()
        )
        
        # Notify admin (Issue 5 - was broken, now sends message to ADMIN_ID)
        admin_notification = f"""
{EMOJI_COLORS['submit']} **New Submission for Review**

**From:** User {user_id}
**Anime:** {context.user_data.get("anime_name")}
**Episodes:** {context.user_data.get("episodes")}
**Genres:** {context.user_data.get("genres")}

**Description:**
{context.user_data.get("synopsis")}
"""
        
        if ADMIN_ID:
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notification, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"[v0] Failed to notify admin of new submission: {e}")
        
        # Reset submission state
        context.user_data["submission_step"] = None
        context.user_data.pop("anime_name", None)
        context.user_data.pop("episodes", None)
        context.user_data.pop("genres", None)
        context.user_data.pop("synopsis", None)

async def accept_submission_disclaimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User accepted disclaimer - proceed to type selection"""
    query = update.callback_query
    
    submission_text = f"""
{EMOJI_COLORS['submit']} **Submit Your Anime**

Great! You've agreed to the terms.

What type are you submitting?
"""
    
    await query.edit_message_text(
        submission_text,
        reply_markup=keyboard_gen.submission_keyboard(),
        parse_mode="Markdown"
    )


async def handle_submission_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle submission type selection (anime vs movie)"""
    query = update.callback_query
    submission_type = query.data.split("_")[2]  # "anime" or "movie"
    
    context.user_data["submission_type"] = submission_type
    context.user_data["submission_step"] = "awaiting_name"
    
    type_text = "Anime" if submission_type == "anime" else "Movie"
    
    await query.edit_message_text(
        f"{EMOJI_COLORS['submit']} Submit {type_text}\n\n"
        f"What's the title of the {type_text}?\n\n"
        f"(Send the name in your next message)"
    )
