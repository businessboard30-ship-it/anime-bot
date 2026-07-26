import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("SINOBANED2_BOT_TOKEN", "your_token_here")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///anime_bot.db")
USE_POSTGRESQL = "postgresql" in DATABASE_URL

# API Configuration
ANILIST_ENDPOINT = "https://graphql.anilist.co"
JIKAN_ENDPOINT = "https://api.jikan.moe/v4"

# Payment Configuration
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
CLONE_BOT_FEE_GHS = 50  # 50 GHS in pesewas = 5000

# Features
MAX_BUTTONS_PER_ROW = 2
PAGINATION_SIZE = 5
RATE_LIMIT_SEARCHES = 10
RATE_LIMIT_SUBMISSIONS = 5

# Emoji Color Codes for UI
EMOJI_COLORS = {
    "trending": "🔥",      # Red/Hot
    "latest": "✨",        # Sparkle/New
    "ongoing": "🔄",       # Cycle/Ongoing
    "season": "📅",        # Calendar
    "movies": "🎬",        # Movie
    "search": "🔍",        # Search
    "submit": "📤",        # Upload
    "admin": "⚙️",         # Settings
    "clone": "🤖",         # Robot
    "categories": "📚",    # Books/Library
    "success": "✅",       # Check
    "error": "❌",         # Cross
    "loading": "⏳",       # Hourglass
    "back": "⬅️",          # Back
    "next": "➡️",          # Next
}

# Animation frames
LOADING_ANIMATION = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# Messages
MESSAGES = {
    "welcome": "Welcome to the Anime & Movies Bot! Choose what you want to explore.",
    "trending_title": "Trending Anime Right Now",
    "latest_title": "Latest Anime Releases",
    "ongoing_title": "Ongoing Series",
    "season_title": "This Season's Anime",
    "movies_title": "Anime Movies",
    "no_results": "No results found. Try another search.",
    "submission_received": "Thank you! Your submission has been received and is under review.",
    "clone_prompt": "Clone this bot for 50 GHS and customize it for yourself!",
    "payment_success": "Payment successful! Setting up your new bot...",
}
