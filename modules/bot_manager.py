"""
Bot Manager Module
BotFather-style management for bots the user already owns, ported from SUPER-BOT.
NOTE: this can only manage bots whose token the user supplies — it cannot mint
new bot tokens, since only Telegram's real @BotFather can do that.
"""

import aiohttp
import logging
from typing import Optional, Dict, List, Tuple
from database import get_pool

logger = logging.getLogger(__name__)


async def tg_call(token: str, method: str, params: Optional[dict] = None) -> dict:
    """Call any Telegram Bot API method against a managed (3rd-party) bot token."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.telegram.org/bot{token}/{method}",
                json=params or {},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"[v0] tg_call {method}: {e}")
        return {"ok": False, "description": str(e)}


async def verify_bot_token(token: str) -> Tuple[bool, dict]:
    """Returns (ok, bot_info_dict_or_error_string)."""
    d = await tg_call(token, "getMe")
    if d.get("ok"):
        return True, d["result"]
    return False, d.get("description", "Invalid token")


async def add_managed_bot(user_id: int, token: str, info: dict) -> bool:
    """Register a verified bot token for this user. False if already registered."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchval(
                "SELECT id FROM managed_bots WHERE user_id = $1 AND token = $2",
                user_id, token
            )
            if existing:
                return False
            await conn.execute(
                "INSERT INTO managed_bots (user_id, token, username, name) VALUES ($1, $2, $3, $4)",
                user_id, token, info.get("username", "unknown"), info.get("first_name", "Bot")
            )
        return True
    except Exception as e:
        logger.error(f"[v0] Error adding managed bot: {e}")
        return False


async def get_user_bots(user_id: int) -> List[Dict]:
    """List all bots this user has registered, ordered by when they were added."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, token, username, name FROM managed_bots WHERE user_id = $1 ORDER BY added_at ASC",
                user_id
            )
        return [{"id": r["id"], "token": r["token"], "username": r["username"], "name": r["name"]} for r in rows]
    except Exception as e:
        logger.error(f"[v0] Error fetching managed bots: {e}")
        return []


async def get_managed_bot(user_id: int, bot_id: int) -> Optional[Dict]:
    """Fetch one managed bot by its DB id, scoped to the owning user."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, token, username, name FROM managed_bots WHERE id = $1 AND user_id = $2",
                bot_id, user_id
            )
        if row:
            return {"id": row["id"], "token": row["token"], "username": row["username"], "name": row["name"]}
        return None
    except Exception as e:
        logger.error(f"[v0] Error fetching managed bot: {e}")
        return None


async def remove_managed_bot(user_id: int, bot_id: int) -> bool:
    """Remove a bot from this user's BotManager list. Only removes the registration —
    the bot itself keeps running."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM managed_bots WHERE id = $1 AND user_id = $2",
                bot_id, user_id
            )
        return result.endswith("1")
    except Exception as e:
        logger.error(f"[v0] Error removing managed bot: {e}")
        return False
