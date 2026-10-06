"""
External Integrations Handler — News, Currency, Stock Charts
Telegram-facing logic for /news, /convert, /stock commands
"""

from telegram import Update
from telegram.ext import ContextTypes
import logging

from modules.external_apis import fetch_news, convert_currency, get_stock_chart

logger = logging.getLogger(__name__)


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
