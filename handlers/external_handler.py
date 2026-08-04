"""
External Integrations Handler — News, Currency, Stock Charts, Media Download
Telegram-facing logic for /news, /convert, /stock, /download commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os

from modules.external_apis import fetch_news, convert_currency, get_stock_chart, download_media, get_crypto_price
from utils.rate_limiter import rate_limiter
from utils import is_owner
from handlers import utility_paywall
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# No domain whitelist: yt-dlp supports 1800+ sites, and hand-maintaining a
# list here just means legitimate links (Facebook and anything else not on
# the old list) got rejected before we even tried. Only DRM-protected sites
# stay blocked here since yt-dlp categorically cannot fetch them (no amount
# of retrying will work) — everything else is attempted and fails with
# yt-dlp's own error message if unsupported. Size is enforced separately
# (pre-download estimate + post-download hard check) in
# modules/external_apis.py so we don't need a domain gate for that either.
DRM_BLOCKED_DOMAINS = {
    "spotify.com", "www.spotify.com", "open.spotify.com",
    "music.apple.com", "netflix.com", "www.netflix.com",
}


# ═══════════════════════════════════════════════════════════════════════════
# NEWS COMMAND
# ═══════════════════════════════════════════════════════════════════════════

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /news <topic>
    Fetch and display top headlines for a topic.
    """
    try:
        # Check if topic provided
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "Usage: /news <topic>\nExample: /news anime\n\nFetch top headlines about any topic."
            )
            return
        
        topic = " ".join(context.args).strip()
        
        if not topic or len(topic) > 100:
            await update.message.reply_text("Topic must be 1-100 characters.")
            return
        
        await update.message.reply_text(f"🔍 Searching news for '{topic}'...")
        
        news = await fetch_news(topic, max_results=5)
        
        if not news:
            await update.message.reply_text(
                f"📰 No news found for '{topic}'. Try a different topic or check spelling."
            )
            return
        
        response = f"📰 **Top News: {topic}**\n\n"
        for i, article in enumerate(news, 1):
            title = article.get("title", "No title")
            if len(title) > 60:
                title = title[:60] + "..."
            url = article.get("url", "#")
            source = article.get("source", "")
            suffix = f" — {source}" if source else ""
            response += f"{i}. [{title}]({url}){suffix}\n"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"[v0] Error in news_command: {e}")
        await update.message.reply_text(f"Error fetching news: {str(e)[:50]}")


# ═══════════════════════════════════════════════════════════════════════════
# CURRENCY CONVERSION COMMAND
# ═══════════════════════════════════════════════════════════════════════════

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /convert <amount> <from> <to>
    Convert currency amounts.
    Example: /convert 100 USD GHS
    """
    try:
        # Check arguments
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "Usage: /convert <amount> <from_currency> <to_currency>\n"
                "Example: /convert 100 USD GHS\n\nSupported currencies: USD, EUR, GBP, GHS, etc."
            )
            return
        
        try:
            amount = float(context.args[0])
            from_currency = context.args[1].upper()
            to_currency = context.args[2].upper()
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid format. Use: /convert <amount> <from> <to>")
            return
        
        if amount <= 0 or amount > 1000000:
            await update.message.reply_text("Amount must be between 0 and 1,000,000.")
            return
        
        await update.message.reply_text(f"💱 Converting {amount} {from_currency} to {to_currency}...")
        
        result = await convert_currency(amount, from_currency, to_currency)
        
        if not result:
            await update.message.reply_text(
                "Currency conversion failed. Check currency codes (e.g., USD, EUR, GBP, GHS)."
            )
            return
        
        response = (
            f"💱 **Currency Conversion**\n\n"
            f"{result['original_amount']} {result['from_currency']} = "
            f"{result['converted_amount']} {result['to_currency']}\n"
            f"Rate: 1 {result['from_currency']} = {result['rate']:.6f} {result['to_currency']}"
        )
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"[v0] Error in convert_command: {e}")
        await update.message.reply_text(f"Error: {str(e)[:50]}")


# ═══════════════════════════════════════════════════════════════════════════
# STOCK CHART COMMAND
# ═══════════════════════════════════════════════════════════════════════════

async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /stock <ticker> [period]
    Fetch stock chart for a ticker symbol.
    Periods: 1d, 5d, 1mo (default), 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    Example: /stock AAPL 6mo
    """
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /stock <ticker> [period]\n"
                "Example: /stock AAPL 1mo\n\n"
                "Periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"
            )
            return
        
        ticker = context.args[0].strip()
        period = context.args[1] if len(context.args) > 1 else "1mo"
        
        if not ticker or len(ticker) > 10:
            await update.message.reply_text("Ticker must be 1-10 characters.")
            return
        
        valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
        if period not in valid_periods:
            await update.message.reply_text(f"Invalid period. Use one of: {', '.join(valid_periods)}")
            return
        
        await update.message.reply_text(f"📈 Fetching stock chart for {ticker} ({period})...")
        
        stock_data = await get_stock_chart(ticker, period)
        
        if not stock_data:
            await update.message.reply_text(f"Stock data not found for ticker: {ticker}")
            return
        
        change_color = "🟢" if stock_data['change_24h_percent'] >= 0 else "🔴"
        
        response = (
            f"📊 **{stock_data['ticker']} Stock Chart**\n\n"
            f"Current Price: ${stock_data['current_price']}\n"
            f"{change_color} 24h Change: {stock_data['change_24h_percent']:+.2f}%\n"
            f"Period: {stock_data['period']}\n"
            f"Data Points: {len(stock_data['data_points'])}\n\n"
            f"_Use a web service like TradingView for interactive charts._"
        )
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"[v0] Error in stock_command: {e}")
        await update.message.reply_text(f"Error: {str(e)[:50]}")


# ═══════════════════════════════════════════════════════════════════════════
# MEDIA DOWNLOAD COMMAND
# ═══════════════════════════════════════════════════════════════════════════

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /download <URL> [audio|video] — or bare /download, or the "⬇️ Download"
    button, drops the user into waiting mode so the next message can just be
    the link, no /download prefix needed.

    Gated by the shared AI Chat + Download paywall (handlers/utility_paywall.py):
    2 free downloads, then a 25 GHS / 2-month subscription that also unlocks
    AI Chat. Founders bypass the paywall entirely.
    """
    try:
        user_id = update.effective_user.id

        if not is_owner(user_id, context):
            allowed, _usage = await utility_paywall.check_access(update, context, "download")
            if not allowed:
                await utility_paywall.send_paywall_message(update, context, "download")
                return

        if not context.args or len(context.args) < 1:
            await _enter_download_waiting_mode(update, context)
            return

        url = context.args[0].strip()
        if len(context.args) > 1 and context.args[1].lower() in ("audio", "video"):
            await _run_download(update, context, url, context.args[1].lower())
        else:
            await _show_format_picker(update, context, url)

    except Exception as e:
        logger.error(f"[v0] Error in download_command: {e}")
        await update.message.reply_text(f"Error: {str(e)[:50]}")


async def _enter_download_waiting_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Puts the user in 'awaiting_download_link' mode — their next message
    is treated as the link to download, no /download prefix needed."""
    context.user_data["awaiting_download_link"] = True
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Exit Download", callback_data="cancel_waiting_mode")]])
    text = (
        "⬇️ **Download**\n\n"
        "Paste the link now — I'll ask whether you want audio or video.\n\n"
        "Type /cancel or tap below to exit."
    )
    query = update.callback_query
    if query:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def start_download_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the '⬇️ Download' button (callback_data 'tools_download_info')."""
    user_id = update.effective_user.id
    if not is_owner(user_id, context):
        allowed, _usage = await utility_paywall.check_access(update, context, "download")
        if not allowed:
            await utility_paywall.send_paywall_message(update, context, "download")
            return
    await _enter_download_waiting_mode(update, context)


async def handle_download_waiting_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routed from handle_message() in api/bot.py when 'awaiting_download_link'
    is set — the user's plain-text message becomes the link to download.

    Stays in this mode after replying, so the user can keep pasting links
    one after another without re-tapping ⬇️ Download each time. Mode only
    ends via /cancel or the 'Exit Download' button (handled in api/bot.py)."""
    text = (update.message.text or "").strip()
    parts = text.split()

    if not parts:
        await update.message.reply_text("Send a link to download. Tap ⬇️ Download to try again.")
        return

    url = parts[0]
    if len(parts) > 1 and parts[1].lower() in ("audio", "video"):
        await _run_download(update, context, url, parts[1].lower())
    else:
        await _show_format_picker(update, context, url)


async def _show_format_picker(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Ask whether this link should be downloaded as audio or video."""
    context.user_data["pending_download_url"] = url
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Audio", callback_data="dl_format_audio"),
            InlineKeyboardButton("🎬 Video", callback_data="dl_format_video"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_waiting_mode")],
    ])
    await update.effective_message.reply_text("What format would you like?", reply_markup=keyboard)


async def handle_download_format_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type: str):
    """Callback from the 🎵 Audio / 🎬 Video picker shown by _show_format_picker."""
    query = update.callback_query
    url = context.user_data.pop("pending_download_url", None)
    if not url:
        await query.answer("That link expired — paste it again.", show_alert=True)
        return
    await query.answer()
    await _run_download(update, context, url, media_type)


async def _run_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, media_type: str):
    """Shared tail end for the /download <args> path, the waiting-mode path,
    and the audio/video picker callback: rate limit, validate, fetch, send,
    then consume a free use if applicable."""
    user_id = update.effective_user.id
    msg = update.effective_message

    if not await rate_limiter.check_download_limit(user_id):
        await msg.reply_text(
            "🚫 You've hit the download limit (5 per hour).\n"
            "Try again later!"
        )
        return

    if media_type not in ["audio", "video"]:
        await msg.reply_text("Media type must be 'audio' or 'video'.")
        return

    if not url.startswith("http"):
        await msg.reply_text("URL must start with http:// or https://")
        return

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if domain in DRM_BLOCKED_DOMAINS or domain.replace("www.", "") in DRM_BLOCKED_DOMAINS:
            await msg.reply_text(
                "❌ This site uses DRM protection (Spotify/Apple Music/Netflix) — "
                "no downloader, including this one, can fetch from it. Try a different link."
            )
            return
        if not domain:
            await msg.reply_text("Invalid URL format.")
            return
    except Exception as e:
        logger.error(f"[v0] URL parsing error: {e}")
        await msg.reply_text("Invalid URL format.")
        return

    await msg.reply_text(f"⏳ Downloading {media_type}... This may take a moment.")

    result = await download_media(url, media_type)

    if "error" in result:
        await msg.reply_text(f"Download failed: {result['error']}")
        return

    filepath = result.get("filepath")
    title = result.get("title", "Media")
    size_mb = result.get("size_mb", 0)

    if not filepath or not os.path.exists(filepath):
        await msg.reply_text("Failed to download media.")
        return

    try:
        with open(filepath, "rb") as file:
            if media_type == "audio":
                await msg.reply_audio(
                    audio=file,
                    title=title[:100],
                    duration=result.get("duration_seconds", 0),
                    caption=f"📥 {title}\n{size_mb}MB • {result.get('uploader', 'Unknown')}"
                )
            else:
                await msg.reply_video(
                    video=file,
                    caption=f"📥 {title}\n{size_mb}MB • {result.get('uploader', 'Unknown')}"
                )

        # Clean up
        os.remove(filepath)

    except Exception as e:
        logger.error(f"[v0] Error sending file: {e}")
        await msg.reply_text(f"Error sending file: {str(e)[:50]}")
        return

    if not is_owner(user_id, context):
        await utility_paywall.consume_free_use(user_id, context, "download")


# ═══════════════════════════════════════════════════════════════════════════
# CRYPTO PRICE COMMAND
# ═══════════════════════════════════════════════════════════════════════════

async def crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /crypto <coin>
    Get current crypto price (uses existing CoinGecko API).
    Example: /crypto bitcoin
    """
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /crypto <coin_name>\n"
                "Example: /crypto bitcoin or /crypto ethereum"
            )
            return
        
        coin = " ".join(context.args).strip()
        
        if not coin or len(coin) > 50:
            await update.message.reply_text("Coin name must be 1-50 characters.")
            return
        
        await update.message.reply_text(f"💰 Fetching price for {coin}...")
        
        price_data = await get_crypto_price(coin)
        
        if not price_data:
            await update.message.reply_text(f"Crypto data not found for: {coin}")
            return
        
        change_emoji = "📈" if price_data.get('change_24h_percent', 0) >= 0 else "📉"
        
        response = (
            f"💰 **{price_data['coin']} Price**\n\n"
            f"USD Price: ${price_data['price_usd']:,.2f}\n"
            f"{change_emoji} 24h Change: {price_data.get('change_24h_percent', 0):+.2f}%\n"
            f"Market Cap: ${price_data.get('market_cap_usd', 0):,.0f}\n"
            f"24h Volume: ${price_data.get('volume_24h_usd', 0):,.0f}"
        )
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"[v0] Error in crypto_command: {e}")
        await update.message.reply_text(f"Error: {str(e)[:50]}")
