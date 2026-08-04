"""
External API Integrations:
- News (using NewsAPI free tier)
- Currency Conversion (using Open Exchange Rates or Free Forex API)
- Stock Charts (using yfinance)
- Media Download (using yt-dlp)
"""

import aiohttp
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# NEWS API
# ═══════════════════════════════════════════════════════════════════════════

async def fetch_news(query: str, max_results: int = 5) -> List[Dict]:
    """
    Fetch top news headlines for a topic via Google News' public RSS feed.

    Chosen over NewsAPI/GNews/Bing News because it needs no API key/signup
    (those either require a paid key or a registered free-tier key we don't
    have configured), has no rate limit to manage, and covers any topic —
    general news, not anime-specific, per how /news is used in this bot.
    Tradeoff: it's an unofficial-but-stable public feed rather than a
    contracted API, so there's no formal uptime/rate-limit guarantee — if
    Google ever changes the RSS format this will need a parser update, same
    caveat as the Yandex reverse-image-search scrape in modules/image_search.py.

    Returns list of {"title": str, "url": str, "source": str, "published": str}.
    Empty list on no results OR on any fetch/parse failure — callers already
    treat an empty list as "no results found".
    """
    import xml.etree.ElementTree as ET
    from urllib.parse import quote as _quote

    url = f"https://news.google.com/rss/search?q={_quote(query)}&hl=en-US&gl=US&ceid=US:en"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning(f"[v0] Google News RSS request failed: status={resp.status}")
                    return []
                body = await resp.text()

        root = ET.fromstring(body)
        items = root.findall("./channel/item")

        results = []
        for item in items[:max_results]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source = source_el.text.strip() if source_el is not None and source_el.text else ""

            if not title or not link:
                continue

            results.append({
                "title": title,
                "url": link,
                "source": source,
                "published": pub_date,
            })

        return results

    except ET.ParseError as e:
        logger.warning(f"[v0] Google News RSS returned unparseable XML: {e}")
        return []
    except Exception as e:
        logger.error(f"[v0] fetch_news('{query}') error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════
# CURRENCY CONVERSION
# ═══════════════════════════════════════════════════════════════════════════

async def convert_currency(amount: float, from_currency: str, to_currency: str) -> Optional[Dict]:
    """
    Convert currency amount using free exchange rate API (exchangerate-api.com or fixer.io).
    Returns dict with: original_amount, from_currency, to_currency, converted_amount, rate, timestamp
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Using exchangerate-api.com free tier (1500 req/month)
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    to_curr = to_currency.upper()
                    
                    if to_curr in data.get("rates", {}):
                        rate = data["rates"][to_curr]
                        converted = amount * rate
                        
                        return {
                            "original_amount": amount,
                            "from_currency": from_currency.upper(),
                            "to_currency": to_curr,
                            "converted_amount": round(converted, 2),
                            "rate": rate,
                            "timestamp": datetime.now().isoformat()
                        }
        
        return None
    
    except Exception as e:
        logger.error(f"[v0] Error converting currency: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# STOCK CHARTS
# ═══════════════════════════════════════════════════════════════════════════

async def get_stock_chart(ticker: str, period: str = "1mo") -> Optional[Dict]:
    """
    Fetch stock price chart data using yfinance.
    Returns dict with: ticker, current_price, 24h_change, data_points (list of {date, price, volume})
    Periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    """
    try:
        import yfinance as yf
        
        # Validate ticker format
        ticker = ticker.upper().strip()
        if not ticker or len(ticker) > 10:
            return None
        
        # Fetch stock data
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            return None
        
        # Extract current price and 24h change
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        change_24h = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
        
        # Build data points for chart
        data_points = [
            {
                "date": str(idx.date()),
                "price": round(float(row['Close']), 2),
                "volume": int(row['Volume']) if row['Volume'] > 0 else 0
            }
            for idx, row in hist.iterrows()
        ]
        
        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "change_24h_percent": round(change_24h, 2),
            "period": period,
            "data_points": data_points[-30:],  # Last 30 points
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"[v0] Error fetching stock chart for {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# MEDIA DOWNLOAD (YouTube, etc.)
# ═══════════════════════════════════════════════════════════════════════════

TELEGRAM_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB (Telegram's limit)

async def download_media(url: str, media_type: str = "audio") -> Optional[Dict]:
    """
    Download audio or video from URL (YouTube, etc.) using yt-dlp.
    media_type: "audio" (m4a/opus, whatever the source provides — no ffmpeg
    transcoding) or "video" (pre-muxed mp4).
    Returns dict with: filename, size_mb, duration_seconds, format
    Respects Telegram's 50MB file size limit.
    """
    try:
        import yt_dlp
        import os
        
        download_dir = "/tmp/media_downloads"
        os.makedirs(download_dir, exist_ok=True)
        
        # Configure yt-dlp
        #
        # Audio: no ffmpeg postprocessing. Vercel's Python runtime has no
        # ffmpeg binary on PATH, so the old FFmpegExtractAudio->mp3 step was
        # silently broken in production. Instead we ask yt-dlp for an
        # already-muxed audio-only stream and send it as-is. m4a is
        # preferred because Telegram's sendAudio API natively supports
        # MP3/M4A; other containers (opus/webm) still work but some clients
        # may show them as a generic file rather than an inline audio player.
        if media_type == "audio":
            format_spec = "bestaudio[ext=m4a]/bestaudio/best"
        else:
            format_spec = "best[ext=mp4]"
        
        ydl_opts = {
            'format': format_spec,
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Pre-flight: pull metadata only (download=False) first so an
            # oversized file is rejected before we spend serverless time and
            # bandwidth actually pulling it down. Not every extractor reports
            # a size up front (filesize/filesize_approx can be None), in
            # which case we fall through to the post-download hard check
            # below rather than guessing.
            try:
                preflight_info = ydl.extract_info(url, download=False)
            except Exception as e:
                return {"error": f"Couldn't read this link: {str(e)[:150]}"}

            estimated_size = preflight_info.get("filesize") or preflight_info.get("filesize_approx")
            if estimated_size and estimated_size > TELEGRAM_MAX_FILE_SIZE:
                return {
                    "error": f"File too large: ~{estimated_size / (1024*1024):.1f}MB. Max allowed: 50MB"
                }

            info = ydl.extract_info(url, download=True)
            
            filepath = ydl.prepare_filename(info)
            filesize = os.path.getsize(filepath)
            
            # Hard check (covers extractors that couldn't report size up front)
            if filesize > TELEGRAM_MAX_FILE_SIZE:
                os.remove(filepath)
                return {
                    "error": f"File too large: {filesize / (1024*1024):.1f}MB. Max allowed: 50MB"
                }
            
            return {
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "size_mb": round(filesize / (1024 * 1024), 2),
                "duration_seconds": info.get('duration', 0),
                "format": media_type,
                "title": info.get('title', 'Media'),
                "uploader": info.get('uploader', 'Unknown')
            }
    
    except Exception as e:
        logger.error(f"[v0] Error downloading media from {url}: {e}")
        return {"error": str(e)[:100]}


# ═══════════════════════════════════════════════════════════════════════════
# CRYPTO PRICES (already exists in superbot but adding here for convenience)
# ═══════════════════════════════════════════════════════════════════════════

async def get_crypto_price(coin: str) -> Optional[Dict]:
    """
    Get current crypto price using CoinGecko API (free, no key required).
    Returns dict with: coin, price_usd, market_cap_usd, volume_24h_usd, change_24h_percent
    """
    try:
        coin = coin.lower().strip()
        
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if coin in data:
                        coin_data = data[coin]
                        return {
                            "coin": coin.upper(),
                            "price_usd": coin_data.get("usd"),
                            "market_cap_usd": coin_data.get("usd_market_cap"),
                            "volume_24h_usd": coin_data.get("usd_24h_vol"),
                            "change_24h_percent": coin_data.get("usd_24h_change"),
                            "timestamp": datetime.now().isoformat()
                        }
        
        return None
    
    except Exception as e:
        logger.error(f"[v0] Error fetching crypto price for {coin}: {e}")
        return None
