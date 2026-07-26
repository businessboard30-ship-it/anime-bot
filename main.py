import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, ADMIN_ID
from database import db
from keyboards import keyboard_gen
from anime_service import anime_service
from formatter import AnimeFormatter
from handlers import discover, search, submit, admin_panel, clone_bot

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AnimeBot:
    """Main Telegram Bot for Anime Discovery"""
    
    def __init__(self, token: str):
        self.token = token
        self.app = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with Gen Z vibes"""
        user = update.effective_user
        
        # Add user to database
        await db.add_user(user.id, user.username or "Anonymous", user.first_name or "User")
        
        welcome_text = f"""
🎬 Yo {user.first_name}! What's good? 🎌

Welcome to the anime spot that actually hits different! 
We got trending, latest, ongoing anime & movies - all the good stuff fr fr.

You can also:
• Drop your fav anime for the world to see 🔥
• Clone this bot and make it your own (50 GHS only!)
• Get AI anime recommendations (10 GHS/month - no cap!)
• Vibe with other anime heads 📺

Ready to find your next obsession? Let's go! 💯
"""
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard_gen.main_menu(),
            parse_mode="Markdown"
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route callback queries to handlers"""
        query = update.callback_query
        callback_data = query.data
        
        await query.answer()
        
        # Routing logic
        if callback_data == "main_menu":
            await self.show_main_menu(update, context)
        
        elif callback_data.startswith("discover_"):
            await discover.handle_discover(update, context)
        
        elif callback_data.startswith("page_"):
            await discover.handle_pagination(update, context)
        
        elif callback_data.startswith("anime_details_"):
            await discover.show_anime_details(update, context)
        
        elif callback_data == "search_anime":
            await search.start_search(update, context)
        
        elif callback_data == "submit_anime":
            await submit.start_submission(update, context)
        
        elif callback_data == "clone_bot":
            await clone_bot.start_clone(update, context)
        
        elif callback_data == "view_categories" or callback_data.startswith("category_"):
            await discover.handle_categories(update, context)
        
        elif callback_data == "admin_panel" and update.effective_user.id == ADMIN_ID:
            await admin_panel.show_admin_panel(update, context)
        
        else:
            await query.edit_message_text("Option not yet implemented.")
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu with Gen Z style"""
        query = update.callback_query
        
        menu_text = """
🎬 **WHAT'S POPPIN'?** 🎌

Pick your vibe:

🔥 **Trending** - The anime that's slaying rn
✨ **Latest** - Fresh drops, no cap
🔄 **Ongoing** - Weekly bangers fr fr
📅 **This Season** - What's hot THIS moment
🎬 **Movies** - Anime movies that hit different
🔍 **Search** - Find that one anime bro
📚 **Categories** - Organized by mood
📤 **Submit** - Drop your fav (we review it!)
🤖 **Clone** - Make your own bot! (50 GHS)
🎮 **AI Recs** - Let AI pick for you (10 GHS/mo)
💼 **/admin** - You know what this is

Tap anything below! Let's goooo 💯
"""
        
        await query.edit_message_text(
            menu_text,
            reply_markup=keyboard_gen.main_menu(),
            parse_mode="Markdown"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        text = update.message.text
        
        if "🔍" in text or text.lower().startswith("search"):
            await search.handle_search_message(update, context)
        elif "📤" in text or text.lower().startswith("submit"):
            await submit.handle_submission_message(update, context)
    
    def setup_handlers(self):
        """Setup all command and message handlers"""
        
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("admin", admin_panel.admin_command))
        
        # Callback query handlers
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def run(self):
        """Run the bot"""
        self.app = Application.builder().token(self.token).build()
        
        # Initialize database
        await db.init()
        
        # Setup handlers
        self.setup_handlers()
        
        print("[v0] Starting Anime Bot...")
        
        async with self.app:
            await self.app.start()
            await self.app.updater.start_polling()
            print("[v0] Bot is polling...")
            await asyncio.Event().wait()

async def main():
    """Main entry point"""
    bot = AnimeBot(BOT_TOKEN)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
