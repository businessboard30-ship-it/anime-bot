"""
Generic "Pay Now" button attached to a group's welcome message.

The admin sets an arbitrary label + amount via /setpaybutton (see
handlers/moderation.py + modules/moderation_extra.py) — this bot doesn't
care what the payment is FOR (paid access, membership, a fundraiser,
whatever); it just runs the existing Paystack initialize/verify flow and
logs it via the generic payment_logs table (database.log_payment /
mark_payment_paid), the same pattern used by clone_bot.py and
utility_paywall.py.

callback_data conventions:
  welcome_pay_init_<chat_id>   -> initialize a Paystack transaction
  welcome_pay_verify_<chat_id> -> verify + confirm in the group
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import db
from payments import paystack
from modules import moderation_extra as modx
from config import EMOJI_COLORS

logger = logging.getLogger(__name__)


async def handle_payment_initiation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """callback_data == 'welcome_pay_init_<chat_id>'"""
    query = update.callback_query
    user = update.effective_user
    chat_id = int(query.data.split("_")[-1])

    pay_button = await modx.get_pay_button(chat_id)
    if not pay_button:
        await query.answer("This payment option is no longer available.", show_alert=True)
        return

    label = pay_button["label"]
    amount_ghs = pay_button["amount_ghs"]
    email = f"user_{user.id}@animebot.com"

    payment_result = paystack.initialize_payment(
        email,
        amount_ghs * 100,  # GHS -> pesewas
        user.id,
        f"GroupPay_{chat_id}_{user.id}",
        payment_type="group_pay_now",
        extra_metadata={"chat_id": chat_id, "label": label},
    )

    if payment_result and payment_result.get("status") == "success":
        reference = payment_result.get("reference")
        payment_link = payment_result.get("authorization_url")

        await db.log_payment(
            user.id, amount_ghs, reference, status="pending",
            payment_type="group_pay_now", chat_id=chat_id,
        )
        context.user_data[f"welcome_pay_ref_{chat_id}"] = reference

        # Sent privately where possible via a URL button rather than a
        # markdown link, so tapping it works the same on every client.
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Pay {amount_ghs} GHS", url=payment_link)],
            [InlineKeyboardButton("✅ I've Paid — Verify", callback_data=f"welcome_pay_verify_{chat_id}")],
        ])
        await query.answer()
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"{EMOJI_COLORS['success']} **{label} — Payment Ready**\n\n"
                f"Amount: GHS {amount_ghs}.00\n\n"
                f"Tap below to pay via Paystack, then come back and tap "
                f"\"I've Paid — Verify\"."
            ),
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    else:
        logger.error(f"[v0] Paystack init failed for group_pay_now, chat {chat_id}, user {user.id}.")
        await query.answer("Failed to initialize payment. Please try again.", show_alert=True)


async def handle_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """callback_data == 'welcome_pay_verify_<chat_id>'"""
    query = update.callback_query
    user = update.effective_user
    chat_id = int(query.data.split("_")[-1])
    reference = context.user_data.get(f"welcome_pay_ref_{chat_id}")

    if not reference:
        await query.answer("Payment reference not found. Tap Pay Now again.", show_alert=True)
        return

    result = paystack.verify_payment(reference)

    if result.get("status") == "success":
        await db.mark_payment_paid(reference)
        context.user_data.pop(f"welcome_pay_ref_{chat_id}", None)
        await query.edit_message_text(f"{EMOJI_COLORS['success']} **Payment confirmed — thank you!**", parse_mode="Markdown")

        # Best-effort notify the group so the admin/community sees it went
        # through. What (if anything) this should unlock beyond that is left
        # to the admin's own process for v1 — the bot only confirms receipt.
        try:
            name = user.first_name or user.username or "Someone"
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ {name} just completed a payment. Thanks!"
            )
        except Exception as e:
            logger.warning(f"[v0] Could not post payment confirmation to chat {chat_id}: {e}")
    else:
        await query.answer("Payment not confirmed yet. Complete checkout, then tap Verify again.", show_alert=True)
