import json
import asyncio
import os
from typing import Dict, Any
from http.server import BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError

# Import all handlers
from handlers.discover import (
    handle_trending, handle_latest, handle_ongoing, 
    handle_seasonal, handle_movies, handle_discover_menu
)
from handlers.search import handle_search
from handlers.submit import handle_submit_start, handle_submit_text
from handlers.admin_panel import handle_admin_menu, handle_admin_callback
from handlers.subscription import handle_subscribe_ai, handle_ai_recommendation, handle_ai_summary
from handlers.clone_bot import handle_clone_start, handle_clone_callback
from keyboards import get_main_menu

# Initialize bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Add handlers
app.add_handler(CommandHandler("start", handle_start))
app.add_handler(CommandHandler("discover", handle_discover_menu))
app.add_handler(CommandHandler("trending", handle_trending))
app.add_handler(CommandHandler("latest", handle_latest))
app.add_handler(CommandHandler("ongoing", handle_ongoing))
app.add_handler(CommandHandler("seasonal", handle_seasonal))
app.add_handler(CommandHandler("movies", handle_movies))
app.add_handler(CommandHandler("search", handle_search))
app.add_handler(CommandHandler("submit", handle_submit_start))
app.add_handler(CommandHandler("subscribe", handle_subscribe_ai))
app.add_handler(CommandHandler("ai_recommend", handle_ai_recommendation))
app.add_handler(CommandHandler("ai_summary", handle_ai_summary))
app.add_handler(CommandHandler("clone", handle_clone_start))
app.add_handler(CommandHandler("admin", handle_admin_menu))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))


async def handle_start(update, context):
    """Start command with Gen Z personality"""
    user = update.effective_user
    
    welcome_message = (
        f"Yo {user.first_name}! 🎬\n\n"
        f"Welcome to AnimeHub - where anime recommendations hit different!\n\n"
        f"What you can do:\n"
        f"🔥 /trending - Most slapped anime rn\n"
        f"✨ /latest - Fresh anime dropped\n"
        f"🔄 /ongoing - Series that slap weekly\n"
        f"📅 /seasonal - This season's bangers\n"
        f"🎬 /movies - Anime movies fr fr\n"
        f"🔍 /search - Find any anime\n"
        f"📤 /submit - Add your fav anime\n"
        f"🤖 /ai_recommend - AI finds anime for you (subscribe: 10 GHS)\n"
        f"🤖 /ai_summary - Gen Z summaries (subscribe: 10 GHS)\n"
        f"🔐 /clone - Create your own bot (50 GHS)\n\n"
        f"Let's find your next binge! 📺"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=get_main_menu())


async def handle_message(update, context):
    """Handle text messages"""
    if context.user_data.get("awaiting_preference"):
        # Handle AI recommendation preference
        preferences = update.message.text
        from groq_service import groq_service
        
        await update.message.reply_text("🤔 Cooking up some recommendations...")
        
        recommendation = await groq_service.get_anime_recommendation(preferences, [])
        await update.message.reply_text(f"Your rec: {recommendation}")
        
        context.user_data["awaiting_preference"] = False
    else:
        await update.message.reply_text(
            "Yo, use /start to see what's available! 👀",
            reply_markup=get_main_menu()
        )


async def handle_callback(update, context):
    """Handle button callbacks"""
    query = update.callback_query
    data = query.data
    
    # Route to appropriate handler based on callback data
    if data.startswith("admin_"):
        await handle_admin_callback(update, context)
    elif data.startswith("clone_"):
        await handle_clone_callback(update, context)
    else:
        await query.answer()


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler for Telegram webhooks"""
    
    def do_POST(self):
        """Handle POST request from Telegram"""
        content_length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        
        # Parse update
        update_data = json.loads(body)
        update = Update.de_json(update_data, app.bot)
        
        # Process update asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(app.process_update(update))
        finally:
            loop.close()
        
        # Send response
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
