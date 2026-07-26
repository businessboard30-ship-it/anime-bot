from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import EMOJI_COLORS, MAX_BUTTONS_PER_ROW, LOADING_ANIMATION

class KeyboardGenerator:
    """Generate organized keyboard layouts with colored buttons"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Main menu with discover categories"""
        keyboard = [
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['trending']} Trending", callback_data="discover_trending"),
                InlineKeyboardButton(f"{EMOJI_COLORS['latest']} Latest", callback_data="discover_latest")
            ],
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['ongoing']} Ongoing", callback_data="discover_ongoing"),
                InlineKeyboardButton(f"{EMOJI_COLORS['season']} Season", callback_data="discover_season")
            ],
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['movies']} Movies", callback_data="discover_movies")
            ],
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['search']} Search", callback_data="search_anime"),
                InlineKeyboardButton(f"{EMOJI_COLORS['categories']} Categories", callback_data="view_categories")
            ],
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['submit']} Submit Anime", callback_data="submit_anime"),
                InlineKeyboardButton(f"{EMOJI_COLORS['clone']} Clone Bot", callback_data="clone_bot")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def anime_list_keyboard(anime_list: list, page: int = 1, category: str = "trending") -> InlineKeyboardMarkup:
        """Generate keyboard for anime list with pagination"""
        keyboard = []
        
        # Each anime as a button
        for anime in anime_list:
            title = anime.get("title", "Unknown")[:30]  # Truncate long titles
            button_text = f"📺 {title}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"anime_details_{anime.get('id')}")
            ])
        
        # Navigation buttons
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(f"{EMOJI_COLORS['back']} Back", callback_data=f"page_{category}_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"Page {page}", callback_data="noop"))
        nav_row.append(InlineKeyboardButton(f"{EMOJI_COLORS['next']} Next", callback_data=f"page_{category}_{page+1}"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([
            InlineKeyboardButton(f"{EMOJI_COLORS['back']} Back to Menu", callback_data="main_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def anime_details_keyboard(anime_id: int) -> InlineKeyboardMarkup:
        """Keyboard for anime details view"""
        keyboard = [
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['submit']} Add to My List", callback_data=f"add_to_list_{anime_id}"),
                InlineKeyboardButton(f"📤 Share", callback_data=f"share_anime_{anime_id}")
            ],
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['back']} Back", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def submission_keyboard() -> InlineKeyboardMarkup:
        """Keyboard for submission workflow"""
        keyboard = [
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['success']} Anime", callback_data="submit_anime_type"),
                InlineKeyboardButton(f"{EMOJI_COLORS['success']} Movie", callback_data="submit_movie_type")
            ],
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['back']} Cancel", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_panel_keyboard() -> InlineKeyboardMarkup:
        """Admin review panel keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['success']} Approve", callback_data="approve_submission"),
                InlineKeyboardButton(f"{EMOJI_COLORS['error']} Reject", callback_data="reject_submission")
            ],
            [
                InlineKeyboardButton(f"📝 Add Note", callback_data="add_admin_note"),
                InlineKeyboardButton(f"⬅️ Skip", callback_data="skip_submission")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def clone_payment_keyboard(amount_ghs: int) -> InlineKeyboardMarkup:
        """Keyboard for clone payment with Paystack"""
        keyboard = [
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['clone']} Pay {amount_ghs} GHS", callback_data="paystack_checkout")
            ],
            [
                InlineKeyboardButton(f"ℹ️ What's Included", callback_data="clone_info"),
                InlineKeyboardButton(f"❌ Cancel", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def clone_customization_keyboard() -> InlineKeyboardMarkup:
        """Keyboard for clone customization"""
        keyboard = [
            [
                InlineKeyboardButton("📝 Edit Bot Name", callback_data="customize_name"),
                InlineKeyboardButton("🔗 Set Webhook URL", callback_data="customize_webhook")
            ],
            [
                InlineKeyboardButton("🎨 Branding", callback_data="customize_branding"),
                InlineKeyboardButton("📂 Categories", callback_data="customize_categories")
            ],
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['success']} Done", callback_data="finalize_clone"),
                InlineKeyboardButton(f"❌ Cancel", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def category_management_keyboard() -> InlineKeyboardMarkup:
        """Keyboard for managing categories"""
        keyboard = [
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['success']} Create New", callback_data="create_category"),
                InlineKeyboardButton("📋 View All", callback_data="view_all_categories")
            ],
            [
                InlineKeyboardButton(f"{EMOJI_COLORS['back']} Back", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def search_keyboard() -> ReplyKeyboardMarkup:
        """Reply keyboard for search input"""
        keyboard = [
            [KeyboardButton("🔍 Search Anime")],
            [KeyboardButton("🔍 Search Movies")],
            ["❌ Cancel"]
        ]
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    @staticmethod
    def get_loading_animation(frame: int) -> str:
        """Get loading animation frame"""
        return LOADING_ANIMATION[frame % len(LOADING_ANIMATION)]

# Global instance
keyboard_gen = KeyboardGenerator()
