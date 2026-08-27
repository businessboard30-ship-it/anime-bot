"""
Ads & Marketplace Handlers
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import EMOJI_COLORS, ADMIN_ID
import flow_state
from modules import ads_marketplace as am
from utils import safe_edit_message


# ── Marketplace ────────────────────────────────────────────────────────

def _market_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ BROWSE SERVICES", callback_data="market_browse_0")],
        [InlineKeyboardButton("➕ LIST A SERVICE", callback_data="market_add")],
        [InlineKeyboardButton("📋 MY LISTINGS", callback_data="market_mine")],
        [InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="main_menu")],
    ])


async def show_market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_edit_message(query, 
        "🛍️ **Services Marketplace**\n\nBuy or sell services with other users.",
        reply_markup=_market_menu_keyboard(),
        parse_mode="Markdown"
    )


async def browse_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """market_browse_<offset>"""
    query = update.callback_query
    offset = int(query.data.split("_")[-1])
    page_size = 5
    listings = await am.get_marketplace_listings(limit=page_size, offset=offset)

    if not listings:
        if offset == 0:
            await safe_edit_message(query, 
                "📭 No services listed yet. Be the first!",
                reply_markup=_market_menu_keyboard()
            )
        else:
            await query.answer("No more listings.", show_alert=True)
        return

    lines = ["🛍️ **Marketplace**\n"]
    rows = []
    for l in listings:
        lines.append(f"• **{l['service_title']}** — ${l['price_usd']:.2f} ({l['category']})")
        rows.append([InlineKeyboardButton(f"👁️ {l['service_title'][:30]}", callback_data=f"market_view_{l['id']}")])

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"market_browse_{max(0, offset - page_size)}"))
    nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"market_browse_{offset + page_size}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_market")])

    await safe_edit_message(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


async def view_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """market_view_<id>"""
    query = update.callback_query
    listing_id = query.data.split("market_view_")[-1]
    listing = await am.get_listing(listing_id)
    if not listing:
        await query.answer("Listing not found.", show_alert=True)
        return

    await am.record_listing_click(listing_id)
    await safe_edit_message(query, 
        f"🛍️ **{listing['service_title']}**\n\n"
        f"{listing.get('description') or 'No description provided.'}\n\n"
        f"💵 Price: **${listing['price_usd']:.2f}**\n"
        f"🏷️ Category: {listing.get('category', 'general')}\n"
        f"👀 Clicks: {listing.get('clicks', 0)}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back to browse", callback_data="market_browse_0")
        ]]),
        parse_mode="Markdown"
    )


async def show_my_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    listings = await am.get_my_listings(user_id)

    if not listings:
        await safe_edit_message(query, 
            "📭 You haven't listed any services yet.",
            reply_markup=_market_menu_keyboard()
        )
        return

    rows = []
    for l in listings:
        rows.append([
            InlineKeyboardButton(f"{l['service_title'][:25]} (${l['price_usd']:.0f})", callback_data=f"market_view_{l['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"market_remove_{l['id']}"),
        ])
    rows.append([InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_market")])
    await safe_edit_message(query, "📋 **My Listings**", reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


async def remove_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """market_remove_<id>"""
    query = update.callback_query
    user_id = update.effective_user.id
    listing_id = query.data.split("market_remove_")[-1]
    await am.deactivate_listing(user_id, listing_id)
    await show_my_listings(update, context)


async def start_add_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """market_add — begins a 4-step text collection flow"""
    query = update.callback_query
    context.user_data["mode"] = "market_add_name"
    context.user_data["market_draft"] = {}
    await flow_state.sync(context, update.effective_user.id, 0, flow="market_add")
    await safe_edit_message(query, 
        "➕ **List a Service**\n\nStep 1/4 — Send a short **service name**:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Cancel", callback_data="m_market")
        ]]),
        parse_mode="Markdown"
    )


async def handle_market_add_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all 4 steps of the market_add_* mode chain."""
    mode = context.user_data.get("mode", "")
    text = update.message.text.strip()
    draft = context.user_data.setdefault("market_draft", {})

    if mode == "market_add_name":
        draft["service_name"] = text[:100]
        context.user_data["mode"] = "market_add_title"
        await flow_state.sync(context, update.effective_user.id, 0, flow="market_add")
        await update.message.reply_text("Step 2/4 — Send a catchy **title** for the listing:", parse_mode="Markdown")

    elif mode == "market_add_title":
        draft["service_title"] = text[:150]
        context.user_data["mode"] = "market_add_desc"
        await flow_state.sync(context, update.effective_user.id, 0, flow="market_add")
        await update.message.reply_text("Step 3/4 — Send a short **description**:", parse_mode="Markdown")

    elif mode == "market_add_desc":
        draft["description"] = text[:1000]
        context.user_data["mode"] = "market_add_price"
        await flow_state.sync(context, update.effective_user.id, 0, flow="market_add")
        await update.message.reply_text("Step 4/4 — Send the **price in USD** (numbers only, e.g. `25`):", parse_mode="Markdown")

    elif mode == "market_add_price":
        try:
            price = float(text.replace("$", "").strip())
        except ValueError:
            await update.message.reply_text("⚠️ Please send a number, e.g. `25` or `25.50`.")
            return
        user_id = update.effective_user.id
        listing_id = await am.list_service(
            user_id, draft.get("service_name", "Service"), draft.get("service_title", "Untitled"),
            draft.get("description", ""), price
        )
        context.user_data.pop("mode", None)
        context.user_data.pop("market_draft", None)
        await flow_state.clear(context, user_id, 0)
        if listing_id:
            await update.message.reply_text(
                f"{EMOJI_COLORS.get('success', '✅')} Listed! Buyers can now find it under Marketplace → Browse.",
                reply_markup=_market_menu_keyboard()
            )
        else:
            await update.message.reply_text(f"{EMOJI_COLORS.get('error', '❌')} Failed to create listing. Try again.")


# ── Ads ─────────────────────────────────────────────────────────────────

def _ads_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 SUBMIT AN AD", callback_data="ads_submit")],
        [InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="main_menu")],
    ])


async def show_ads_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    active = await am.get_active_ads(limit=3)
    text = "📢 **Advertise With Us**\n\nSubmit an ad for owner review — approved ads get shown to users.\n"
    if active:
        text += "\n**Currently running:**\n"
        for a in active:
            text += f"• {a['ad_title']} — {a['company_name']}\n"
    await safe_edit_message(query, text, reply_markup=_ads_menu_keyboard(), parse_mode="Markdown")


async def start_submit_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ads_submit — begins a 5-step text collection flow"""
    query = update.callback_query
    context.user_data["mode"] = "ads_submit_company"
    context.user_data["ad_draft"] = {}
    await flow_state.sync(context, update.effective_user.id, 0, flow="ads_submit")
    await safe_edit_message(query, 
        "📢 **Submit an Ad**\n\nStep 1/5 — Send your **company name**:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Cancel", callback_data="m_ads")
        ]]),
        parse_mode="Markdown"
    )


async def handle_ads_submit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all 5 steps of the ads_submit_* mode chain."""
    mode = context.user_data.get("mode", "")
    text = update.message.text.strip()
    draft = context.user_data.setdefault("ad_draft", {})

    if mode == "ads_submit_company":
        draft["company_name"] = text[:150]
        context.user_data["mode"] = "ads_submit_title"
        await flow_state.sync(context, update.effective_user.id, 0, flow="ads_submit")
        await update.message.reply_text("Step 2/5 — Send the **ad title**:", parse_mode="Markdown")

    elif mode == "ads_submit_title":
        draft["ad_title"] = text[:150]
        context.user_data["mode"] = "ads_submit_desc"
        await flow_state.sync(context, update.effective_user.id, 0, flow="ads_submit")
        await update.message.reply_text("Step 3/5 — Send the **ad description**:", parse_mode="Markdown")

    elif mode == "ads_submit_desc":
        draft["ad_description"] = text[:1000]
        context.user_data["mode"] = "ads_submit_url"
        await flow_state.sync(context, update.effective_user.id, 0, flow="ads_submit")
        await update.message.reply_text("Step 4/5 — Send the **target URL**:", parse_mode="Markdown")

    elif mode == "ads_submit_url":
        draft["target_url"] = text[:500]
        context.user_data["mode"] = "ads_submit_budget"
        await flow_state.sync(context, update.effective_user.id, 0, flow="ads_submit")
        await update.message.reply_text("Step 5/5 — Send your **budget in USD** (numbers only):", parse_mode="Markdown")

    elif mode == "ads_submit_budget":
        try:
            budget = float(text.replace("$", "").strip())
        except ValueError:
            await update.message.reply_text("⚠️ Please send a number, e.g. `100`.")
            return
        user_id = update.effective_user.id
        ad_id = await am.submit_ad(
            user_id, draft.get("company_name", ""), draft.get("ad_title", ""),
            draft.get("ad_description", ""), draft.get("target_url", ""), budget
        )
        context.user_data.pop("mode", None)
        context.user_data.pop("ad_draft", None)
        await flow_state.clear(context, user_id, 0)
        if ad_id:
            await update.message.reply_text(
                f"{EMOJI_COLORS.get('success', '✅')} Ad submitted for review! We'll notify approved advertisers.",
                reply_markup=_ads_menu_keyboard()
            )
            try:
                if ADMIN_ID:
                    await context.bot.send_message(
                        ADMIN_ID,
                        f"📢 New ad submitted (#{ad_id}) from `{user_id}`: *{draft.get('ad_title')}*\n"
                        f"Use /pendingads to review.",
                        parse_mode="Markdown"
                    )
            except Exception:
                pass
        else:
            await update.message.reply_text(f"{EMOJI_COLORS.get('error', '❌')} Failed to submit ad. Try again.")


# ── Admin: pending ads review ────────────────────────────────────────────

async def cmd_pending_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: /pendingads — lists ads awaiting approval with inline actions"""
    if update.effective_user.id != ADMIN_ID:
        return
    pending = await am.get_pending_ads()
    if not pending:
        await update.message.reply_text("📭 No pending ads.")
        return
    for ad in pending:
        await update.message.reply_text(
            f"📢 **#{ad['id']}** — {ad['ad_title']}\n"
            f"🏢 {ad['company_name']}\n"
            f"📝 {ad['ad_description']}\n"
            f"🔗 {ad['target_url']}\n"
            f"💵 Budget: ${ad['budget_usd']:.2f}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve", callback_data=f"ad_approve_{ad['id']}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"ad_reject_{ad['id']}"),
            ]]),
            parse_mode="Markdown"
        )


async def handle_approve_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ad_approve_<id>"""
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Admin only.", show_alert=True)
        return
    ad_id = int(query.data.split("_")[-1])
    ok = await am.approve_ad(ad_id)
    if ok:
        ad = await am.get_ad(ad_id)
        await safe_edit_message(query, f"✅ Approved ad #{ad_id}.")
        if ad:
            try:
                await context.bot.send_message(
                    ad["user_id"],
                    f"🎉 Your ad *{ad['ad_title']}* was approved and is now live!",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
    else:
        await query.answer("Already handled or not found.", show_alert=True)


async def start_reject_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ad_reject_<id> — prompts admin for a reason"""
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Admin only.", show_alert=True)
        return
    ad_id = int(query.data.split("_")[-1])
    context.user_data["mode"] = f"ads_reject_reason_{ad_id}"
    await flow_state.sync(context, update.effective_user.id, 0, flow="ads_reject")
    await safe_edit_message(query, f"Send a rejection reason for ad #{ad_id}:")


async def handle_reject_reason_message(update: Update, context: ContextTypes.DEFAULT_TYPE, ad_id: int):
    reason = update.message.text.strip()
    context.user_data.pop("mode", None)
    await flow_state.clear(context, update.effective_user.id, 0)
    ok = await am.reject_ad(ad_id, reason)
    if ok:
        ad = await am.get_ad(ad_id)
        await update.message.reply_text(f"❌ Rejected ad #{ad_id}.")
        if ad:
            try:
                await context.bot.send_message(
                    ad["user_id"], f"⚠️ Your ad *{ad['ad_title']}* was rejected: {reason}", parse_mode="Markdown"
                )
            except Exception:
                pass
    else:
        await update.message.reply_text("⚠️ Already handled or not found.")
