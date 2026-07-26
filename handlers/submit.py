from telegram import Update
from telegram.ext import ContextTypes

from database import db
from keyboards import keyboard_gen
from formatter import AnimeFormatter
from config import EMOJI_COLORS, ADMIN_ID

async def start_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start anime submission workflow"""
    query = update.callback_query
    
    submission_text = f"""
{EMOJI_COLORS['submit']} **Submit Your Anime**

Share an anime or movie you'd like to contribute to our database.

What type are you submitting?
"""
    
    await query.edit_message_text(
        submission_text,
        reply_markup=keyboard_gen.submission_keyboard(),
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
        
        # Submit to database
        submission_id = await db.add_submission(
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
        
        # Notify admin
        from main import AnimeBot
        admin_notification = f"""
{EMOJI_COLORS['submit']} **New Submission for Review**

**From:** User {user_id}
**Anime:** {context.user_data.get("anime_name")}
**Episodes:** {context.user_data.get("episodes")}
**Genres:** {context.user_data.get("genres")}

**Description:**
{context.user_data.get("synopsis")}
"""
        
        # Reset submission state
        context.user_data["submission_step"] = None
        context.user_data.pop("anime_name", None)
        context.user_data.pop("episodes", None)
        context.user_data.pop("genres", None)
        context.user_data.pop("synopsis", None)

async def handle_submission_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle submission type selection (anime vs movie)"""
    query = update.callback_query
    submission_type = query.data.split("_")[2]  # "anime" or "movie"
    
    context.user_data["submission_type"] = submission_type
    context.user_data["submission_step"] = "awaiting_name"
    
    type_text = f"Anime" if submission_type == "anime" else "Movie"
    
    await query.edit_message_text(
        f"{EMOJI_COLORS['submit']} Submit {type_text}\n\n"
        f"What's the title of the {type_text}?\n\n"
        f"(Send the name in your next message)"
    )
