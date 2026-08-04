from telegram import Update
from telegram.ext import ContextTypes

from anime_service import anime_service
from keyboards import keyboard_gen
from config import EMOJI_COLORS
from utils import escape_markdown_v1 as esc_md
from utils.rate_limiter import rate_limiter

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start search workflow"""
    query = update.callback_query

    search_text = f"""
{EMOJI_COLORS['search']} **Search Anime**

Send me the name of an anime or movie you want to find.
"""

    if query:
        await query.edit_message_text(
            search_text,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            search_text,
            parse_mode="Markdown"
        )

    # Set context for next message handler
    context.user_data["mode"] = "search"

async def handle_search_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search query from user message"""
    user_message = update.message.text
    user_id = update.effective_user.id
    
    if "cancel" in user_message.lower():
        await update.message.reply_text(
            "Search cancelled.",
            reply_markup=keyboard_gen.main_menu()
        )
        context.user_data.pop("mode", None)
        return
    
    # Rate limit: RATE_LIMIT_SEARCHES per hour (Issue 1.3)
    if not await rate_limiter.check_search_limit(user_id):
        await update.message.reply_text(
            f"{EMOJI_COLORS['error']} You've hit your search limit for now. "
            f"Try again in an hour."
        )
        context.user_data.pop("mode", None)
        return
    
    # Show loading
    loading_msg = await update.message.reply_text(f"{EMOJI_COLORS['loading']} Searching...")
    
    # Search anime
    results = await anime_service.search_anime(user_message)
    
    if results:
        message = f"{EMOJI_COLORS['search']} **Search Results for '{esc_md(user_message)}'**\n\n"
        for i, anime in enumerate(results, 1):
            rating = anime.get("rating", 0)
            episodes = anime.get("episodes", "?")
            message += f"{i}. {esc_md(anime.get('title'))}\n"
            message += f"   Episodes: {episodes} | Rating: {rating:.1f}/10\n\n"
        
        await loading_msg.edit_text(
            message,
            reply_markup=keyboard_gen.anime_list_keyboard(results, 1, "search"),
            parse_mode="Markdown"
        )
    else:
        await loading_msg.edit_text(
            f"{EMOJI_COLORS['error']} No anime found for '{esc_md(user_message)}'.\n\nTry a different search term.",
            reply_markup=keyboard_gen.main_menu()
        )
    
    context.user_data.pop("mode", None)
