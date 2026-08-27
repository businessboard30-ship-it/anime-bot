"""
Admin Tools — bot-wide analytics, CSV export, chat self-registration.
Ported from SUPER-BOT's cmd_analytics/cmd_exportusers/cmd_registerme, rewritten
against this repo's real Postgres schema instead of the original's in-memory
dict iteration.
"""

import csv
import io
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from config import ADMIN_ID
from database import get_pool


async def cmd_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: /analytics — bot-wide usage analytics"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Owner only.")
        return

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            active_today = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE joined_date::date = $1", date.today()
            )
            premium_n = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE tier != 'free' OR user_id = $1", ADMIN_ID
            )
            total_ai_chat = await conn.fetchval("SELECT COUNT(*) FROM ai_chat_usage")
            total_ai_image = await conn.fetchval("SELECT COUNT(*) FROM ai_image_usage")
            # clone_id = 0 restricts this to the main bot's own groups —
            # this table is shared with every clone, so an unscoped count
            # here would include groups that belong to clones, not this bot.
            groups_n = await conn.fetchval(
                "SELECT COUNT(*) FROM bot_group_membership WHERE bot_status IN ('member', 'administrator') "
                "AND clone_id = 0"
            )
            bots_n = await conn.fetchval("SELECT COUNT(*) FROM managed_bot_tokens")
    except Exception as e:
        print(f"[v0] Error building analytics: {e}")
        await update.message.reply_text("⚠️ Couldn't build analytics right now. Check logs.")
        return

    await update.message.reply_text(
        f"📈 *BOT ANALYTICS*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total users: *{total_users}*\n"
        f"🟢 Joined today: *{active_today}*\n"
        f"👑 Premium/paid tier users: *{premium_n}*\n\n"
        f"🤖 AI chat uses (all-time): *{total_ai_chat}*\n"
        f"🎨 AI image generations (all-time): *{total_ai_image}*\n\n"
        f"👥 Groups/channels connected: *{groups_n}*\n"
        f"🛠️ Bots registered (Bot Manager): *{bots_n}*",
        parse_mode="Markdown"
    )


async def cmd_exportusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: /exportusers — export all user records as CSV"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Owner only.")
        return

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id, username, first_name, tier, subscription_status, joined_date FROM users"
            )
    except Exception as e:
        print(f"[v0] Error exporting users: {e}")
        await update.message.reply_text("⚠️ Export failed. Check logs.")
        return

    buf = io.StringIO()
    fieldnames = ["user_id", "username", "first_name", "tier", "subscription_status", "joined_date"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(dict(r))

    data = io.BytesIO(buf.getvalue().encode("utf-8"))
    data.name = f"users_export_{date.today().isoformat()}.csv"
    await update.message.reply_document(data, caption=f"📁 {len(rows)} user records exported.")


async def cmd_addsponsor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: /addsponsor <runs> | <button label> | <button url> | <text...>
    Queues a sponsored post to be injected into the autopost cron cycle."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Owner only.")
        return

    raw = update.message.text.partition(" ")[2].strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 4:
        await update.message.reply_text(
            "Usage:\n`/addsponsor <runs> | <button label> | <button url> | <message text>`\n\n"
            "Example:\n`/addsponsor 5 | Visit Us | https://example.com | Check out our new feature!`",
            parse_mode="Markdown"
        )
        return

    try:
        runs = int(parts[0])
    except ValueError:
        await update.message.reply_text("⚠️ First field (runs) must be a number.")
        return

    button_label, button_url, content = parts[1], parts[2], " | ".join(parts[3:])

    from database import db
    sponsored_id = await db.add_sponsored_post(update.effective_user.id, content, button_label, button_url, runs)
    if sponsored_id:
        await update.message.reply_text(
            f"✅ Sponsored post #{sponsored_id} queued — will run {runs} time(s), "
            f"injected into the autopost cron cycle."
        )
    else:
        await update.message.reply_text("⚠️ Failed to queue sponsored post. Check logs.")


async def cmd_registerme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-of-this-group-only: /registerme — registers the current group/
    channel so it receives broadcasts and auto-posts."""
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("⚠️ This command only works inside a group or channel.")
        return

    try:
        member = await context.bot.get_chat_member(chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("⚠️ Only admins can register this chat.")
            return
    except TelegramError:
        pass  # can't verify (e.g. channel with limited member info) — allow it through

    clone_config = context.bot_data.get("clone_config")
    clone_id = clone_config.get("clone_id") if clone_config else 0

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bot_group_membership (group_id, clone_id, bot_status)
                VALUES ($1, $2, 'member')
                ON CONFLICT (group_id, clone_id) DO UPDATE SET bot_status = 'member'
            """, chat.id, clone_id)
    except Exception as e:
        print(f"[v0] Error registering chat: {e}")
        await update.message.reply_text("⚠️ Registration failed. Check logs.")
        return

    await update.message.reply_text(
        f"✅ *{chat.title or 'This chat'}* has been registered!\n"
        f"It will now receive broadcasts and auto-posts. 📡",
        parse_mode="Markdown"
    )
