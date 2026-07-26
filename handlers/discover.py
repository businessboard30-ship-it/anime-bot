from telegram import Update
from telegram.ext import ContextTypes

from anime_service import anime_service
from keyboards import keyboard_gen
from formatter import AnimeFormatter
from config import EMOJI_COLORS

# Store pagination state
user_pages = {}
anime_cache = {}

async def handle_discover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle discover category selection"""
    query = update.callback_query
    user_id = update.effective_user.id
    callback_data = query.data
    
    # Parse category
    category = callback_data.replace("discover_", "")
    
    loading_msg = f"{EMOJI_COLORS['loading']} Fetching anime..."
    await query.edit_message_text(loading_msg)
    
    # Fetch anime based on category
    anime_list = []
    title = ""
    
    if category == "trending":
        anime_list = await anime_service.get_trending_anime()
        title = f"{EMOJI_COLORS['trending']} Trending Anime"
    elif category == "latest":
        anime_list = await anime_service.get_latest_anime()
        title = f"{EMOJI_COLORS['latest']} Latest Releases"
    elif category == "ongoing":
        anime_list = await anime_service.get_ongoing_anime()
        title = f"{EMOJI_COLORS['ongoing']} Ongoing Series"
    elif category == "season":
        anime_list = await anime_service.get_seasonal_anime()
        title = f"{EMOJI_COLORS['season']} This Season"
    elif category == "movies":
        # For movies, we'd need a separate query
        anime_list = await anime_service.get_seasonal_anime()
        title = f"{EMOJI_COLORS['movies']} Anime Movies"
    
    # Store for pagination
    user_pages[user_id] = {"category": category, "page": 1}
    cache_key = f"{user_id}_{category}_1"
    anime_cache[cache_key] = anime_list
    
    if anime_list:
        message = f"{title}\n\n"
        for i, anime in enumerate(anime_list, 1):
            rating = anime.get("rating", 0)
            message += f"{i}. {anime.get('title')} - {rating:.1f}/10\n"
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard_gen.anime_list_keyboard(anime_list, 1, category),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"{EMOJI_COLORS['error']} No anime found in this category.",
            reply_markup=keyboard_gen.main_menu()
        )

async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pagination through anime lists"""
    query = update.callback_query
    user_id = update.effective_user.id
    callback_data = query.data
    
    # Parse: page_<category>_<page_number>
    parts = callback_data.split("_")
    category = parts[1]
    page = int(parts[2])
    
    loading_msg = f"{EMOJI_COLORS['loading']} Loading page {page}..."
    await query.edit_message_text(loading_msg)
    
    # Fetch anime for this page
    anime_list = []
    
    if category == "trending":
        anime_list = await anime_service.get_trending_anime(page)
    elif category == "latest":
        anime_list = await anime_service.get_latest_anime(page)
    elif category == "ongoing":
        anime_list = await anime_service.get_ongoing_anime(page)
    elif category == "season":
        anime_list = await anime_service.get_seasonal_anime(page)
    
    user_pages[user_id] = {"category": category, "page": page}
    
    if anime_list:
        message = f"{EMOJI_COLORS['latest']} Page {page}\n\n"
        for i, anime in enumerate(anime_list, 1):
            rating = anime.get("rating", 0)
            message += f"{i}. {anime.get('title')} - {rating:.1f}/10\n"
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard_gen.anime_list_keyboard(anime_list, page, category),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"{EMOJI_COLORS['error']} No more results.",
            reply_markup=keyboard_gen.main_menu()
        )

async def show_anime_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed info about an anime"""
    query = update.callback_query
    callback_data = query.data
    
    anime_id = int(callback_data.replace("anime_details_", ""))
    
    loading_msg = f"{EMOJI_COLORS['loading']} Loading details..."
    await query.edit_message_text(loading_msg)
    
    # Fetch details from API
    anime = await anime_service.get_anime_details(anime_id)
    
    if anime:
        details_text = AnimeFormatter.format_anime_card(anime)
        await query.edit_message_text(
            details_text,
            reply_markup=keyboard_gen.anime_details_keyboard(anime_id),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"{EMOJI_COLORS['error']} Could not load anime details.",
            reply_markup=keyboard_gen.main_menu()
        )

async def handle_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category viewing"""
    query = update.callback_query
    
    categories_text = f"""
{EMOJI_COLORS['categories']} **Your Categories**

Create custom categories to organize anime by genre, season, or preference.

"""
    
    await query.edit_message_text(
        categories_text,
        reply_markup=keyboard_gen.category_management_keyboard(),
        parse_mode="Markdown"
    )
