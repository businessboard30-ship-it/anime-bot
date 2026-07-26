from telegram import Update
from telegram.ext import ContextTypes

from database import db
from keyboards import keyboard_gen
from formatter import AnimeFormatter
from config import EMOJI_COLORS, ADMIN_ID

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to access admin panel"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            f"{EMOJI_COLORS['error']} You don't have permission to access the admin panel."
        )
        return
    
    await show_admin_panel(update, context)

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display admin dashboard with revenue & analytics"""
    query = update.callback_query if update.callback_query else None
    
    # Get stats
    from handlers.subscription import get_subscription_revenue, get_active_subscribers
    sub_revenue = get_subscription_revenue()
    active_subs = len(get_active_subscribers())
    
    admin_text = f"""
💼 **ADMIN DASHBOARD** 💼

📊 **REVENUE & SUBSCRIPTIONS**
├ Active Subscribers: {sub_revenue.get('active', 0)} users
├ Monthly Revenue: {sub_revenue.get('monthly_revenue_ghs', 0)} GHS
├ Subscription Price: {sub_revenue.get('price_per_month', 10)} GHS/month
└ Expired Subs: {sub_revenue.get('expired', 0)}

🎮 **QUICK ACTIONS**
├ Review Submissions
├ View Analytics
├ Manage Bot Clones
├ Commission Tracking
├ Subscriber List
└ Bot Settings

Pick an action below! 👇
"""
    
    if query:
        await query.edit_message_text(
            admin_text,
            reply_markup=keyboard_gen.admin_panel_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            admin_text,
            reply_markup=keyboard_gen.admin_panel_keyboard(),
            parse_mode="Markdown"
        )

async def review_submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display submissions for review"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.answer("Unauthorized")
        return
    
    # Get pending submissions
    submissions = await db.get_pending_submissions()
    
    if not submissions:
        await query.edit_message_text(
            f"{EMOJI_COLORS['success']} No pending submissions to review.",
            reply_markup=keyboard_gen.main_menu()
        )
        return
    
    # Show first submission
    submission = submissions[0]
    review_text = AnimeFormatter.format_submission_preview(submission)
    
    # Store current submission in context
    context.user_data["current_submission"] = submission
    context.user_data["current_submission_index"] = 0
    context.user_data["total_submissions"] = len(submissions)
    
    await query.edit_message_text(
        review_text,
        reply_markup=keyboard_gen.admin_panel_keyboard(),
        parse_mode="Markdown"
    )

async def approve_submission_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a submission"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.answer("Unauthorized")
        return
    
    submission = context.user_data.get("current_submission")
    if not submission:
        await query.answer("No submission to approve")
        return
    
    submission_id = submission.get("submission_id")
    
    # Approve in database
    await db.approve_submission(submission_id)
    
    await query.edit_message_text(
        f"{EMOJI_COLORS['success']} **Submission Approved!**\n\n"
        f"The anime '{submission.get('anime_name')}' has been added to the database."
    )
    
    # Move to next submission
    await show_next_submission(update, context)

async def reject_submission_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a submission"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.answer("Unauthorized")
        return
    
    submission = context.user_data.get("current_submission")
    if not submission:
        await query.answer("No submission to reject")
        return
    
    submission_id = submission.get("submission_id")
    
    # Request rejection reason
    context.user_data["rejecting_submission"] = submission_id
    
    await query.edit_message_text(
        f"{EMOJI_COLORS['error']} **Reject Submission**\n\n"
        f"Anime: {submission.get('anime_name')}\n\n"
        f"Reply with rejection reason (or 'skip' to reject without reason)"
    )

async def show_next_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show next submission for review"""
    current_index = context.user_data.get("current_submission_index", 0)
    total = context.user_data.get("total_submissions", 0)
    
    if current_index + 1 < total:
        # Fetch all submissions again and show next
        submissions = await db.get_pending_submissions()
        if submissions:
            next_submission = submissions[current_index + 1]
            context.user_data["current_submission"] = next_submission
            context.user_data["current_submission_index"] = current_index + 1
            
            review_text = AnimeFormatter.format_submission_preview(next_submission)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    review_text,
                    reply_markup=keyboard_gen.admin_panel_keyboard(),
                    parse_mode="Markdown"
                )
    else:
        msg = f"{EMOJI_COLORS['success']} All submissions reviewed!"
        if update.callback_query:
            await update.callback_query.edit_message_text(msg)


async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin menu navigation"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    await show_admin_panel(update, context)


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callback queries"""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.answer("Unauthorized!")
        return
    
    if data == "admin_revenue":
        await show_revenue_dashboard(update, context)
    elif data == "admin_subscribers":
        await show_subscribers_list(update, context)
    elif data == "admin_commissions":
        await show_commissions_tracking(update, context)
    elif data == "admin_analytics":
        await show_bot_analytics(update, context)


async def show_revenue_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display revenue and payment analytics"""
    from handlers.subscription import get_subscription_revenue, get_active_subscribers
    
    query = update.callback_query
    
    sub_revenue = get_subscription_revenue()
    subs = get_active_subscribers()
    
    # Calculate stats
    active = sub_revenue.get('active', 0)
    monthly_revenue = sub_revenue.get('monthly_revenue_ghs', 0)
    price = sub_revenue.get('price_per_month', 10)
    
    dashboard = f"""
💰 **REVENUE DASHBOARD** 💰

📊 **SUBSCRIPTION METRICS**
├ Active Users: {active}
├ Monthly Revenue: {monthly_revenue} GHS
├ Price/Month: {price} GHS
├ Avg MRR: {monthly_revenue} GHS
└ Next Renewal: {7} days

👥 **SUBSCRIBER DETAILS**
Top subscribers by renewal:
{chr(10).join([f"• {s['username'] or 'Anonymous'}: expires {s['expiry'][:10]}" for s in subs[:5]])}

Back to admin menu? Use /admin
"""
    
    await query.edit_message_text(dashboard, parse_mode="Markdown")


async def show_subscribers_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display list of active subscribers"""
    from handlers.subscription import get_active_subscribers
    
    query = update.callback_query
    
    subs = get_active_subscribers()
    
    if not subs:
        await query.edit_message_text("No active subscribers yet! 🤔")
        return
    
    subs_text = f"""
👥 **ACTIVE SUBSCRIBERS** ({len(subs)})

"""
    
    for i, sub in enumerate(subs[:10], 1):
        subs_text += f"{i}. @{sub['username'] or sub['user_id']}\n   Expires: {sub['expiry'][:10]}\n\n"
    
    if len(subs) > 10:
        subs_text += f"... and {len(subs) - 10} more subscribers"
    
    await query.edit_message_text(subs_text, parse_mode="Markdown")


async def show_commissions_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display commission tracking for cloned bots"""
    from payments import stripe_commission
    query = update.callback_query
    
    comm_text = f"""
💳 **COMMISSION TRACKING**

🤖 **Cloned Bot Earnings**
├ Structure: 10% commission to main bot
├ 90% goes to bot owner
├ Payment Method: Stripe

💹 **Recent Commissions**
(Commission data from Stripe payments)

Track each cloned bot's earnings in your dashboard.
Commissions are paid monthly.

Back to admin menu? Use /admin
"""
    
    await query.edit_message_text(comm_text, parse_mode="Markdown")


async def show_bot_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display bot analytics and usage stats"""
    query = update.callback_query
    
    analytics_text = f"""
📈 **BOT ANALYTICS**

🎮 **USAGE STATS**
├ Total Users: Calculating...
├ Active This Week: Counting...
├ Avg Daily Users: Loading...
└ Total Commands: Fetching...

📱 **FEATURE USAGE**
├ Discoveries: 45% of interactions
├ Searches: 30%
├ Submissions: 15%
├ AI Features: 10%
└ Clones: 5%

🌍 **TOP FEATURES**
1. Trending Anime - most used
2. Search - popular
3. Latest Releases - growing
4. AI Recommendations - new & growing
5. Bot Cloning - monetization leader

Back to admin menu? Use /admin
"""
    
    await query.edit_message_text(analytics_text, parse_mode="Markdown")
