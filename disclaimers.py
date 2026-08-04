"""Disclaimer templates and management for user submissions and content"""

from utils import escape_markdown_v1 as esc_md

EMOJI_COLORS = {
    'warning': '⚠️',
    'legal': '⚖️',
    'info': 'ℹ️',
    'accept': '✅',
    'decline': '❌'
}

# ==============================================================================
# SUBMISSION DISCLAIMERS
# ==============================================================================

SUBMISSION_DISCLAIMER_COPYRIGHT = f"""
{EMOJI_COLORS['legal']} **COPYRIGHT & LEGAL DISCLAIMER**

By submitting this anime/movie to our directory, you confirm:

✓ You have the right to submit this content
✓ The information provided is factually accurate
✓ You're not violating any copyright laws
✓ You own or have permission for any images/links shared

The bot reserves the right to remove submissions that:
• Violate copyright or intellectual property rights
• Contain illegal streaming links
• Have false/misleading information
• Infringe on third-party rights

If you're unsure about legality of a link, don't submit it.
"""

SUBMISSION_DISCLAIMER_CONTENT = f"""
{EMOJI_COLORS['warning']} **CONTENT WARNING**

This anime/movie may contain:
⚠️ Violence, blood, or gore
⚠️ Sexual or suggestive content
⚠️ Profanity or strong language
⚠️ Psychological themes
⚠️ Other mature material

Users are responsible for age-appropriate viewing.
Parents/guardians should review before allowing minors to watch.
"""

SUBMISSION_DISCLAIMER_FULL = f"""
{EMOJI_COLORS['legal']} **SUBMISSION AGREEMENT**

{SUBMISSION_DISCLAIMER_COPYRIGHT}

{SUBMISSION_DISCLAIMER_CONTENT}

By clicking ✅ ACCEPT, you agree to all terms above.
"""

# ==============================================================================
# VIDEO LINK DISCLAIMERS
# ==============================================================================

LEGAL_STREAMING_SOURCES = f"""
{EMOJI_COLORS['info']} **WHERE TO WATCH LEGALLY**

Free streaming options (with ads):
✓ Crunchyroll (free tier)
✓ Funimation (free tier)
✓ Netflix (some free content)
✓ YouTube (official channels)
✓ HiDive (free tier)

Paid streaming:
• Netflix
• Crunchyroll Premium
• Funimation Premium
• HiDive
• Amazon Prime Video
• Disney+

Never use:
❌ Illegal streaming sites
❌ Torrent downloads
❌ Unauthorized mirrors
❌ Sites without proper licensing
"""

LINK_WARNING = f"""
{EMOJI_COLORS['warning']} **VIDEO LINK WARNING**

Before sharing a link, verify it's from:

✓ Official anime studio channels
✓ Licensed streaming platforms
✓ Official distribution partners
✓ Public domain content

Do NOT share:
❌ Illegal streaming site links
❌ Pirated content links
❌ Unofficial rips
❌ Torrent/download links

Illegal content will be removed and may result in ban.
"""

# ==============================================================================
# STREAMING SERVICE DETECTION
# ==============================================================================

LEGAL_DOMAINS = {
    'crunchyroll.com': 'Crunchyroll',
    'funimation.com': 'Funimation',
    'netflix.com': 'Netflix',
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'hidive.com': 'HiDive',
    'hulu.com': 'Hulu',
    'primevideo.com': 'Amazon Prime',
    'disneyplus.com': 'Disney+',
    'myanimelist.net': 'MyAnimeList',
    'anilist.co': 'AniList',
    'archive.org': 'Internet Archive',
    'animekisa.tv': 'AnimeKisa (Limited)',  # Some free content
}

ILLEGAL_KEYWORDS = [
    'kissanime',
    'gogoanime',
    'animefrenzy',
    'anime4you',
    'pirate',
    'torrent',
    'magnet:',
    '9anime',
    'animestan',
    'kawaiifu',
    'wco.tv',
    'animepahe',
    'animesimple',
    'zoro',
    'masterani',
]

def check_link_legality(url: str) -> tuple[bool, str]:
    """Check if a URL is from a legal source or has suspicious content
    
    Returns:
        (is_legal: bool, message: str)
    """
    if not url:
        return False, "No URL provided"
    
    url_lower = url.lower()
    
    # Check against illegal keywords
    for keyword in ILLEGAL_KEYWORDS:
        if keyword in url_lower:
            return False, f"URL contains '{esc_md(keyword)}' - appears to be illegal streaming site"
    
    # Check if from known legal domain
    for domain, service in LEGAL_DOMAINS.items():
        if domain in url_lower:
            return True, f"✓ Verified legal source: {esc_md(service)}"
    
    # Unknown domain - warn user
    return None, "Unknown source - verify it's from an official/licensed platform"


# ==============================================================================
# SUBMISSION FLOW FUNCTIONS
# ==============================================================================

async def show_submission_disclaimer(update, context):
    """Show copyright + content disclaimer before submission"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("✅ I Agree", callback_data="accept_disclaimer"),
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
        ]
    ]
    
    await update.message.reply_text(
        SUBMISSION_DISCLAIMER_FULL,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_link_warning(update, context):
    """Show legal streaming sources and warning before accepting links"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Understood", callback_data="submit_anime_continue"),
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
        ]
    ]
    
    await update.message.reply_text(
        LEGAL_STREAMING_SOURCES + "\n\n" + LINK_WARNING,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def validate_submission_link(update, context, url: str) -> bool:
    """Validate that submitted link is legal
    
    Returns True if legal/safe to add, False if illegal
    """
    is_legal, message = check_link_legality(url)
    
    if is_legal is False:
        # Illegal link detected
        await update.message.reply_text(
            f"{EMOJI_COLORS['warning']} **BLOCKED: Illegal Link**\n\n{esc_md(message)}\n\n"
            f"This link cannot be added. {LEGAL_STREAMING_SOURCES}",
            parse_mode="Markdown"
        )
        return False
    
    elif is_legal is None:
        # Unknown source - ask for confirmation
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, it's legal", callback_data="confirm_link"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_link")
            ]
        ]
        
        await update.message.reply_text(
            f"{EMOJI_COLORS['warning']} **UNKNOWN SOURCE**\n\n{esc_md(message)}\n\n"
            f"Is this URL from an official/licensed streaming platform?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return None  # Waiting for confirmation
    
    else:
        # Legal link
        await update.message.reply_text(
            f"{EMOJI_COLORS['accept']} {esc_md(message)}\n\nLink approved!",
            parse_mode="Markdown"
        )
        return True


# ==============================================================================
# ADMIN SETTINGS FOR DISCLAIMERS
# ==============================================================================

DEFAULT_DISCLAIMER_CONFIG = {
    "show_copyright": True,
    "show_content_warning": True,
    "require_acceptance": True,
    "check_link_legality": True,
    "block_illegal_links": True,
    "legal_sources_only": False,  # If True, only allow links from LEGAL_DOMAINS
    "custom_disclaimer_text": None,
}
