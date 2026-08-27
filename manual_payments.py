"""Manual payment review flow for every paid feature."""
import json
import logging
from typing import Any, Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import ADMIN_ID
from database import db
from utils import safe_edit_message

logger = logging.getLogger(__name__)


def review_keyboard(reference: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"payment_approve:{reference}")],
        [InlineKeyboardButton("Reject", callback_data=f"payment_reject:{reference}")],
    ])


async def request_review(context, *, user_id: int, reference: str, payment_type: str,
                         clone_id: int = 0, details: Optional[Dict[str, Any]] = None) -> bool:
    """Create a pending review and DM the admin. Repeated taps are harmless."""
    details = details or {}
    status = await db.create_manual_payment_review(
        reference, user_id, payment_type, clone_id, details
    )
    if status == "already_decided":
        return False
    if status == "duplicate":
        await context.bot.send_message(chat_id=user_id, text="Your payment is already awaiting admin review.")
        return True
    # status == "created": brand new review, notify the admin now.
    summary = [
        "Payment review requested",
        f"Type: {payment_type}",
        f"User ID: {user_id}",
        f"Reference: {reference}",
        f"Clone ID: {clone_id}",
    ]
    for key, value in details.items():
        summary.append(f"{key}: {value}")
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="\n".join(summary),
        reply_markup=review_keyboard(reference),
    )
    await context.bot.send_message(
        chat_id=user_id,
        text="Thanks. Your payment report was sent to the admin. Access will be enabled after approval.",
    )
    return True


async def decide_review(context, reference: str, admin_id: int, approved: bool) -> Optional[Dict[str, Any]]:
    if admin_id != ADMIN_ID:
        return None
    review = await db.decide_manual_payment_review(reference, admin_id, approved)
    if not review:
        return None
    return review


async def grant_review(context, review: Dict[str, Any]) -> None:
    """Grant only from stored server-side payment type/context."""
    user_id = int(review["user_id"])
    clone_id = int(review.get("clone_id") or 0)
    payment_type = review["payment_type"]
    details = review.get("context") or {}
    if payment_type == "ai_subscription":
        from handlers.subscription import activate_subscription
        await activate_subscription(user_id, months=1, clone_id=clone_id)
    elif payment_type == "utility_subscription":
        from config import UTILITY_SUB_DAYS
        await db.activate_utility_subscription(user_id, days=UTILITY_SUB_DAYS, clone_id=clone_id)
    elif payment_type == "image_search_unlock":
        await db.mark_image_search_paid(user_id, clone_id=clone_id)
    elif payment_type == "yandex_subscription":
        from config import IMAGE_SEARCH_YANDEX_DAYS
        await db.activate_image_search_yandex_subscription(user_id, clone_id, IMAGE_SEARCH_YANDEX_DAYS)
    elif payment_type == "premium_group":
        await db.set_premium_tier(user_id, clone_id=clone_id)
    elif payment_type == "superbot_tier":
        from modules import superbot_adapter
        await superbot_adapter.set_user_tier(user_id, details["tier"])
    elif payment_type == "botstore_premium":
        from modules import botstore_adapter
        await botstore_adapter.activate_premium(user_id)
    elif payment_type == "group_pay_now":
        await db.mark_payment_paid(review["reference"])
        chat_id = int(details["chat_id"])
        await context.bot.send_message(chat_id=chat_id, text="Payment approved by the admin.")
    elif payment_type == "clone_monetization":
        from config import CLONE_MONETIZATION_DAYS
        await db.activate_monetization_subscription(clone_id, days=CLONE_MONETIZATION_DAYS)
    elif payment_type == "bot_clone":
        await db.mark_clone_payment_paid(review["reference"])


async def handle_admin_decision(update, context) -> None:
    query = update.callback_query
    reference = query.data.split(":", 1)[1]
    approved = query.data.startswith("payment_approve:")
    review = await decide_review(context, reference, update.effective_user.id, approved)
    if not review:
        await query.answer("Unauthorized or already decided.", show_alert=True)
        return
    if approved:
        await grant_review(context, review)
        message = "Approved and access granted."
    else:
        message = "Payment rejected."
    await context.bot.send_message(chat_id=review["user_id"], text=message)
    await safe_edit_message(query, f"{message}\nReference: {reference}")
    await query.answer(message)


async def notify_existing_payment(context, user_id: int, reference: str, payment_type: str,
                                  clone_id: int = 0, details: Optional[Dict[str, Any]] = None):
    return await request_review(context, user_id=user_id, reference=reference,
                                payment_type=payment_type, clone_id=clone_id, details=details)


async def handle_user_verification(update, context, callback_data: str) -> bool:
    """Intercept every paid-feature verification tap; never call a provider API.

    The reference (and any small bit of context, like a superbot tier or a
    welcome_pay chat_id) is looked up from pending_payment_intents - written
    to Postgres at 'Pay Now' time - rather than context.user_data, since a
    Vercel serverless cold start can drop context.user_data between the two
    taps. context.user_data is still checked first as a same-instance fast
    path, but the database is the source of truth.
    """
    user_id = update.effective_user.id
    clone_id = int((context.bot_data.get("clone_config") or {}).get("clone_id") or 0)
    mappings = {
        "verify_utility_sub": ("utility_payment_reference", "utility_subscription"),
        "verify_tier_payment": ("tier_payment_reference", "superbot_tier"),
        "premium_pay_verify": ("premium_group_pay_ref", "premium_group"),
        "imgsearch_verify": ("image_search_payment_reference", "image_search_unlock"),
        "imgsearch_yandex_verify": ("yandex_sub_payment_reference", "yandex_subscription"),
        "verify_botstore_premium": ("botstore_premium_payment_reference", "botstore_premium"),
        "verify_subscription": ("subscription_payment_reference", "ai_subscription"),
    }
    match = next(((key, kind) for prefix, (key, kind) in mappings.items() if callback_data == prefix), None)
    chat_id = None
    if callback_data.startswith("welcome_pay_verify_"):
        chat_id = int(callback_data.rsplit("_", 1)[-1])
        key, kind = (f"welcome_pay_ref_{chat_id}", "group_pay_now")
    elif match:
        key, kind = match
    else:
        return False

    reference = context.user_data.get(key)
    details: Dict[str, Any] = {"chat_id": chat_id} if chat_id is not None else {}
    if not reference:
        intent = await db.get_latest_pending_payment_intent(user_id, kind, chat_id=chat_id)
        if intent:
            reference = intent["reference"]
            stored_context = intent.get("context") or {}
            if isinstance(stored_context, str):
                stored_context = json.loads(stored_context)
            details = {**stored_context, **details}

    if not reference:
        await update.callback_query.answer("Payment reference not found.", show_alert=True)
        return True

    await request_review(context, user_id=user_id, reference=reference, payment_type=kind,
                         clone_id=clone_id, details=details)
    context.user_data.pop(key, None)
    await db.delete_pending_payment_intent(reference)
    await update.safe_edit_message(callback_query, "Payment report sent to the admin. Access will be enabled after approval.")
    return True


__all__ = ["request_review", "notify_existing_payment", "handle_admin_decision", "handle_user_verification"]


def serialize_context(value: Dict[str, Any]) -> str:
    return json.dumps(value, default=str)
