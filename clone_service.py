"""
Real Telegram bot-cloning support (Part 3 of the master brief).

This module talks directly to the raw Telegram Bot API over HTTP (not through
python-telegram-bot's Application, since we don't have an Application for a
clone's token until *after* we've validated it and decided to register it).

Every function here is a thin, honestly-labeled wrapper around one Telegram
API call. None of them do anything "clever" — the cleverness lives in
handlers/clone_bot.py (the flow) and api/bot.py (the routing).
"""
import logging
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"
REQUEST_TIMEOUT = 10


def _call(token: str, method: str, **params) -> Dict[str, Any]:
    """
    Make a raw Telegram Bot API call. Always returns a dict with at least
    {"ok": bool}. Never raises — network/HTTP failures are folded into
    {"ok": False, "error": "..."} so callers can handle them uniformly.
    """
    url = TELEGRAM_API_BASE.format(token=token, method=method)
    try:
        resp = requests.post(url, json=params, timeout=REQUEST_TIMEOUT)
        try:
            data = resp.json()
        except ValueError:
            return {"ok": False, "error": f"Non-JSON response (HTTP {resp.status_code})"}
        if not data.get("ok"):
            data.setdefault("error", data.get("description", "Unknown Telegram API error"))
        return data
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"Network error calling Telegram API: {e}"}


def validate_bot_token(token: str) -> Dict[str, Any]:
    """
    Step A: validate a pasted token is real by calling getMe.

    Returns:
        {"ok": True, "username": "...", "id": ..., "first_name": "..."} on success
        {"ok": False, "error": "..."} on failure (bad token, deleted bot, network issue)
    """
    token = (token or "").strip()
    if not token or ":" not in token:
        return {"ok": False, "error": "That doesn't look like a Telegram bot token (expected format: 123456:ABC-DEF...)."}

    result = _call(token, "getMe")
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "Telegram rejected this token.")}

    info = result.get("result", {})
    if not info.get("is_bot"):
        return {"ok": False, "error": "That token belongs to a user account, not a bot."}

    return {
        "ok": True,
        "username": info.get("username"),
        "id": info.get("id"),
        "first_name": info.get("first_name"),
    }


def get_webhook_info(token: str) -> Dict[str, Any]:
    """
    Step B (pre-check): call getWebhookInfo so we can warn the customer if
    this bot token is already wired up to something else before we overwrite it.

    Returns {"ok": True, "url": "..."} (url is "" if no webhook is set) or
    {"ok": False, "error": "..."}.
    """
    result = _call(token, "getWebhookInfo")
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "Could not fetch webhook info.")}
    info = result.get("result", {})
    return {"ok": True, "url": info.get("url", "") or ""}


def set_webhook(token: str, url: str, secret_token: str) -> Dict[str, Any]:
    """
    Step B: register the clone's webhook, scoped to its own per-clone secret.

    Returns {"ok": True} or {"ok": False, "error": "..."} with Telegram's own
    error message surfaced, not a generic one.
    """
    result = _call(
        token,
        "setWebhook",
        url=url,
        secret_token=secret_token,
        allowed_updates=["message", "callback_query", "my_chat_member"],
        drop_pending_updates=False,
    )
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "setWebhook failed.")}
    return {"ok": True}


def delete_webhook(token: str) -> Dict[str, Any]:
    """
    Used on deactivation: stop Telegram from pushing updates for a token we
    no longer want to route. Returns {"ok": True/False, ...}.
    """
    result = _call(token, "deleteWebhook", drop_pending_updates=False)
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "deleteWebhook failed.")}
    return {"ok": True}
