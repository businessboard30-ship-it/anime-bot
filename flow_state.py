"""
Durable, DB-backed replacement for using context.user_data alone to track
"which step is this user on" in a multi-step wizard flow.

Root cause this addresses (same as the pending_payment_intents fix for
manual payments — see database.py / manual_payments.py): on Vercel
serverless, each incoming Telegram webhook update can be handled by a
completely separate function instance with no shared memory, so
context.user_data set while replying to message N is often gone by the
time message N+1 arrives. For a wizard flow that means the dispatcher's
mode-check in api/bot.py finds nothing set and either silently drops the
flow or misinterprets the next message as belonging to an earlier step.

FLOW_KEYS lists every context.user_data key any wizard flow uses to track
its step or draft data. context.user_data is still the fast path (no DB
round-trip needed when the same instance handles both messages), but
`database.user_flow_state` is the source of truth: every time a handler
sets one of these keys it must call `sync()` afterward, and the dispatcher
calls `hydrate()` once at the top of handle_message/handle_media_message
so a cold instance gets the flow's state back before routing the message.
"""
from typing import Any, Dict

from database import db

# Every context.user_data key used by any of the flows below to track step
# or draft data. Keep this in sync when adding a new wizard flow — a key
# left out of this list will keep working on a warm instance but will not
# survive a cold start, which is exactly the bug this module exists to fix.
FLOW_KEYS = (
    # autopost (handlers/autopost_handler.py)
    "mode", "autopost_target_chat_id", "autopost_interval_minutes",
    # broadcast (handlers/broadcast_handler.py)
    "broadcast_draft", "broadcast_scope", "broadcast_exempt_groups",
    # clone customization / bot manager onboarding (handlers/clone_bot.py)
    "customize_step", "editing_clone_id", "editing_clone_field",
    "clone_name", "clone_webhook", "clone_branding", "clone_categories",
    "pending_clone_token", "pending_clone_username", "pending_clone_first_name",
    "awaiting_payment_key", "awaiting_price_edit",
    # bot manager: add-bot / setname / setdesc / setcmds all live in "mode"
    # (e.g. "addbot", "botmgr_setname_<id>") so no extra keys needed here.
    # ads marketplace / listings (handlers/ads_marketplace_handler.py)
    "market_draft", "ad_draft",
    # botstore (handlers/botstore_handler.py)
    "botstore_mode", "listing_title", "listing_desc", "listing_identifier",
    "listing_type", "submit_step",
    # games (handlers/games_handler.py)
    "trivia", "riddle_ans", "guess_num", "guess_tries",
    # crypto alerts (handlers/superbot_handler.py)
    "alert_step", "alert_coin", "alert_target",
    # inline AI prompts routed directly in api/bot.py
    "awaiting_preference", "awaiting_summary_title",
)


# Keys whose in-memory value is a set (not JSON-serializable) - stored as a
# list and converted back to a set on hydrate.
_SET_KEYS = ("broadcast_exempt_groups",)


def _snapshot(context) -> Dict[str, Any]:
    snap = {k: context.user_data[k] for k in FLOW_KEYS if k in context.user_data}
    for k in _SET_KEYS:
        if k in snap and isinstance(snap[k], set):
            snap[k] = list(snap[k])
    return snap


def _restore_types(data: Dict[str, Any]) -> Dict[str, Any]:
    for k in _SET_KEYS:
        if k in data and isinstance(data[k], list):
            data[k] = set(data[k])
    return data


async def sync(context, user_id: int, clone_id: int, flow: str = "generic"):
    """Persist whatever flow-relevant keys are currently in context.user_data
    to the DB. Call this right after setting/updating any key in FLOW_KEYS.
    If none of those keys are present (flow finished/cancelled), clears the
    DB row instead so a stale row can't be replayed back later."""
    snapshot = _snapshot(context)
    if snapshot:
        await db.save_user_flow_state(user_id, clone_id, flow, snapshot)
    else:
        await db.clear_user_flow_state(user_id, clone_id)


async def hydrate(context, user_id: int, clone_id: int) -> bool:
    """Fast path: if any FLOW_KEYS value is already in context.user_data
    (same warm instance served the previous message), do nothing. Otherwise
    fall back to the DB snapshot and repopulate context.user_data from it.
    Returns True if state was restored from the DB.
    Call this once, before any mode-based routing checks."""
    if any(k in context.user_data for k in FLOW_KEYS):
        return False
    row = await db.get_user_flow_state(user_id, clone_id)
    if not row:
        return False
    context.user_data.update(_restore_types(row["data"]))
    return True


async def clear(context, user_id: int, clone_id: int):
    """Clear flow state from both context.user_data and the DB. Use this
    wherever a flow currently does context.user_data.pop("mode", None) (or
    equivalent) on completion/cancel."""
    for k in FLOW_KEYS:
        context.user_data.pop(k, None)
    await db.clear_user_flow_state(user_id, clone_id)
