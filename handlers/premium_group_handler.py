"""
Premium Group paywall — the "Pay to Join Premium Group" button attached to
every admin broadcast (see api/cron_broadcast.py's _send_broadcast).

Unlike handlers/welcome_pay.py (a per-group, admin-configured amount), this
is a single fixed-price offer for the whole bot: config.PREMIUM_GROUP_FEE_GHS
GHS to join config.PREMIUM_GROUP_INVITE_LINK. Same generic Selar
initialize/verify flow and payment_logs table as the rest of the bot
(clone_bot.py, utility_paywall.py, welcome_pay.py) — just a different
payment_type label ("premium_group_join") to tell them apart in the logs.

callback_data conventions:
  premium_pay_init    -> initialize a Selar transaction (sent privately)
  premium_pay_verify  -> verify + hand over the invite link
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import db
from paystack import paystack
from config import ADMIN_ID, EMOJI_COLORS, PREMIUM_GROUP_FEE_GHS, PREMIUM_GROUP_INVITE_LINK, PREMIUM_GROUP_CHAT_ID
from utils import is_owner, safe_edit_message

logger = logging.getLogger(__name__)


def _clone_id(context) -> int:
    """0 for the main bot, else the running clone's id — pricing lookups must
    be scoped to this so a clone owner's custom price never leaks onto the
    main bot or another clone."""
    clone_config = context.bot_data.get("clone_config")
    return clone_config.get("clone_id") if clone_config else 0


def premium_group_button(price_ghs: float = PREMIUM_GROUP_FEE_GHS) -> InlineKeyboardButton:
    """The single button other modules (broadcast_runner.py) attach to their
    own keyboards — kept here so the label/price/callback stay in one place.
    Callers running inside a clone should pass that clone's own price (via
    db.get_clone_price(clone_id, "premium_group_fee")); this default only
    applies for the main bot / callers that haven't been updated yet."""
    return InlineKeyboardButton(
        f"💎 AZIGI GROUP JOIN — GHS {price_ghs:g}",
        callback_data="premium_pay_init"
    )


AZIGI_DOWNLOAD_CALLBACK = "azigi_download"
AZIGI_LISTINGS_KEY = "azigi_listings"


def azigi_download_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("📥 Download Latest AZIGI", callback_data=AZIGI_DOWNLOAD_CALLBACK)


async def _get_azigi_listings() -> list:
    raw = await db.get_config(AZIGI_LISTINGS_KEY)
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


async def add_azigi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin wizard: /addazigi, then send a photo with its title as caption."""
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["awaiting_azigi_photo"] = True
    await update.message.reply_text(
        "Send the AZIGI image now. Put the listing title in the photo caption.\n"
        "Example: AZIGI v3.2 — Latest release"
    )


async def save_azigi_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.user_data.get("awaiting_azigi_photo") or not update.message.photo:
        return
    title = (update.message.caption or "").strip()
    if not title:
        await update.message.reply_text("Please resend the image with the AZIGI title in the caption.")
        return
    listings = await _get_azigi_listings()
    listings.insert(0, {"file_id": update.message.photo[-1].file_id, "title": title[:200]})
    saved = await db.update_config(AZIGI_LISTINGS_KEY, json.dumps(listings[:30]))
    context.user_data.pop("awaiting_azigi_photo", None)
    await update.message.reply_text("AZIGI listing saved." if saved else "AZIGI listing saved in memory only.")


async def list_azigi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    listings = await _get_azigi_listings()
    await update.message.reply_text("\n".join(f"{i}. {item['title']}" for i, item in enumerate(listings, 1)) or "No AZIGI listings yet.")


async def show_azigi_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show every admin-listed AZIGI release; every item is protected by the group join payment."""
    price = await db.get_clone_price(_clone_id(context), "premium_group_fee")
    listings = await _get_azigi_listings()
    query = update.callback_query
    if query:
        await safe_edit_message(query, "📥 **AZIGI Downloads**\n\nChoose a release below. Join the Premium Group to download.", parse_mode="Markdown")
        target = update.effective_chat.id
    else:
        target = update.effective_chat.id
        await update.message.reply_text("📥 **AZIGI Downloads**\n\nChoose a release below. Join the Premium Group to download.", parse_mode="Markdown")
    if not listings:
        await context.bot.send_message(target, "No AZIGI releases have been listed yet.")
        return
    for item in listings:
        await context.bot.send_photo(
            target, item["file_id"], caption=item["title"],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"💎 Join Premium Group — GHS {price:g}", callback_data="premium_pay_init")]])
        )


async def create_premium_invite_link(bot, user_id: int) -> str:
    """A single-use, 24h invite link when PREMIUM_GROUP_CHAT_ID is set (the
    bot must be an admin there with 'Invite users' rights), so the paying user
    joins instantly and the link can't be shared. Falls back to the static
    PREMIUM_GROUP_INVITE_LINK."""
    if PREMIUM_GROUP_CHAT_ID:
        try:
            link = await bot.create_chat_invite_link(
                chat_id=int(PREMIUM_GROUP_CHAT_ID),
                name=f"paid-{user_id}"[:32],
                member_limit=1,
                expire_date=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            return link.invite_link
        except Exception as e:
            logger.error(f"[v0] Could not create premium invite link for {user_id}: {e}")
    return PREMIUM_GROUP_INVITE_LINK


async def deliver_premium_group_access(bot, user_id: int) -> bool:
    """DM the paid user their personal join button. Used by every payment
    completion path (admin approval, Selar webhook, owner bypass)."""
    link = await create_premium_invite_link(bot, user_id)
    if not link:
        logger.warning("[v0] No PREMIUM_GROUP_CHAT_ID or PREMIUM_GROUP_INVITE_LINK set — can't auto-join paid user.")
        await bot.send_message(
            chat_id=user_id,
            text="✅ Payment confirmed! An admin will add you to the Premium Group shortly.",
        )
        return False
    await bot.send_message(
        chat_id=user_id,
        text=(
            "✅ Payment confirmed! Welcome to the Premium Group.\n\n"
            "Tap below to join — this link is just for you and works once."
        ),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Join Premium Group", url=link)]]),
    )
    return True


async def handle_premium_pay_init(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """callback_data == 'premium_pay_init' — works from any chat (DM, group,
    or channel comment), always follows up in the user's DM so payment
    details never sit in a group feed."""
    query = update.callback_query
    user = update.effective_user

    if is_owner(user.id, context):
        link = await create_premium_invite_link(context.bot, user.id)
        if link:
            await safe_edit_message(query,
                f"{EMOJI_COLORS.get('success', '✅')} Owner bypass — no payment needed.\n\n"
                f"Tap below to join the Premium Group:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Join Premium Group", url=link)]
                ])
            )
        else:
            await query.answer("Owner bypass — but no premium group is configured yet.", show_alert=True)
        return

    clone_id = _clone_id(context)
    price = await db.get_clone_price(clone_id, "premium_group_fee")
    email = f"user_{user.id}@animebot.com"
    payment_result = paystack.initialize_payment(
        email,
        int(price * 100),  # GHS -> pesewas
        user.id,
        f"PremiumGroup_{user.id}",
        payment_type="premium_group_join",
        extra_metadata={"clone_id": clone_id},
    )

    if payment_result and payment_result.get("status") == "success":
        reference = payment_result.get("reference")
        payment_link = payment_result.get("authorization_url")

        await db.log_payment(user.id, price, reference, status="pending")
        # Persisted server-side (not context.user_data) so the 'I've Paid' tap
        # - handled by manual_payments.handle_user_verification, which may run
        # on a different serverless instance - can still find it.
        await db.create_pending_payment_intent(reference, user.id, "premium_group")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Pay GHS {price:g}", url=payment_link)],
            [InlineKeyboardButton("✅ I've Paid — Verify", callback_data="premium_pay_verify")],
        ])

        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"{EMOJI_COLORS.get('success', '✅')} **Premium Group — Payment Ready**\n\n"
                    f"Amount: GHS {price:g}.00\n\n"
                    f"Tap below to pay via Selar, then come back and tap "
                    f"\"I've Paid — Verify\" to get your invite link."
                ),
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            await query.answer("Check your DMs to complete payment 💬")
        except Exception as e:
            logger.warning(f"[v0] Could not DM premium-group payment link to {user.id}: {e}")
            await query.answer(
                "Please start a DM with the bot first, then tap this button again.",
                show_alert=True
            )
    else:
        logger.error(f"[v0] Selar init failed for premium_group_join, user {user.id}.")
        await query.answer("Failed to initialize payment. Please try again.", show_alert=True)


async def handle_premium_pay_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """callback_data == 'premium_pay_verify'"""
    query = update.callback_query
    reference = context.user_data.get("premium_group_pay_ref")

    if not reference:
        await query.answer("Payment reference not found. Tap Pay Now again.", show_alert=True)
        return

    result = paystack.verify_payment(reference)

    if result.get("status") == "success":
        await db.mark_payment_paid(reference)
        context.user_data.pop("premium_group_pay_ref", None)

        if PREMIUM_GROUP_INVITE_LINK:
            await safe_edit_message(query, 
                f"{EMOJI_COLORS.get('success', '✅')} **Payment confirmed!**\n\n"
                f"Tap below to join the Premium Group:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Join Premium Group", url=PREMIUM_GROUP_INVITE_LINK)]
                ])
            )
        else:
            # Configured amount but no invite link set yet — don't leave the
            # user with nothing after paying.
            await safe_edit_message(query, 
                f"{EMOJI_COLORS.get('success', '✅')} **Payment confirmed!** "
                f"An admin will add you to the Premium Group shortly."
            )
            logger.warning("[v0] PREMIUM_GROUP_INVITE_LINK is not set — paid user has no invite link to tap.")
    else:
        await query.answer("Payment not confirmed yet. Complete checkout, then tap Verify again.", show_alert=True)
