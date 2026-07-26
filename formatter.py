from typing import Dict, List
from config import EMOJI_COLORS

class AnimeFormatter:
    """Format anime data for display"""
    
    @staticmethod
    def format_anime_card(anime: Dict) -> str:
        """Format anime as a readable card"""
        title = anime.get("title", "Unknown")
        episodes = anime.get("episodes", "?")
        genres = anime.get("genres", "N/A")
        rating = anime.get("rating", 0)
        description = anime.get("description", "")
        
        card = f"""
{EMOJI_COLORS['success']} **{title}**

{EMOJI_COLORS['ongoing']} Episodes: {episodes}
{EMOJI_COLORS['trending']} Rating: {rating:.1f}/10
{EMOJI_COLORS['categories']} Genres: {genres}

{EMOJI_COLORS['latest']} Synopsis:
{description}
"""
        return card.strip()
    
    @staticmethod
    def format_trending_list(anime_list: List[Dict]) -> str:
        """Format trending anime list"""
        if not anime_list:
            return f"{EMOJI_COLORS['error']} No anime found!"
        
        message = f"{EMOJI_COLORS['trending']} **TRENDING NOW**\n\n"
        for i, anime in enumerate(anime_list, 1):
            title = anime.get("title", "Unknown")[:40]
            rating = anime.get("rating", 0)
            message += f"{i}. {title} ({rating:.1f}/10)\n"
        
        return message
    
    @staticmethod
    def format_submission_preview(submission: Dict) -> str:
        """Format user submission for review"""
        anime_name = submission.get("anime_name", "Unknown")
        episodes = submission.get("episodes", "?")
        genres = submission.get("genres", "N/A")
        synopsis = submission.get("synopsis", "No description")
        user_id = submission.get("user_id", "Unknown")
        
        preview = f"""
{EMOJI_COLORS['submit']} **SUBMISSION REVIEW**

**Title:** {anime_name}
**Episodes:** {episodes}
**Genres:** {genres}
**From User:** {user_id}

**Description:**
{synopsis}
"""
        return preview.strip()
    
    @staticmethod
    def format_clone_info() -> str:
        """Format clone feature info"""
        info = f"""
{EMOJI_COLORS['clone']} **Clone Bot Feature - 50 GHS**

With your own bot clone, you get:

{EMOJI_COLORS['success']} Custom bot name
{EMOJI_COLORS['success']} Custom webhook URL for submissions
{EMOJI_COLORS['success']} Branding & description
{EMOJI_COLORS['success']} Service categories
{EMOJI_COLORS['success']} All anime discovery features
{EMOJI_COLORS['success']} Admin review panel

Your cloned bot will be independent and ready to use!
"""
        return info.strip()
    
    @staticmethod
    def format_payment_message(amount_ghs: int, user_name: str) -> str:
        """Format payment instruction message"""
        message = f"""
{EMOJI_COLORS['success']} **Payment Required**

Dear {user_name},

To clone your personal anime bot, please pay:

**Amount: GHS {amount_ghs}.00**
**Method: Paystack**

Click the payment button below to complete the transaction securely.

{EMOJI_COLORS['loading']} Processing your payment...
"""
        return message.strip()
    
    @staticmethod
    def format_admin_stats(total_users: int, pending_submissions: int, active_clones: int) -> str:
        """Format admin dashboard stats"""
        stats = f"""
{EMOJI_COLORS['admin']} **ADMIN DASHBOARD**

{EMOJI_COLORS['success']} Total Users: {total_users}
{EMOJI_COLORS['submit']} Pending Reviews: {pending_submissions}
{EMOJI_COLORS['clone']} Active Clones: {active_clones}
"""
        return stats.strip()
