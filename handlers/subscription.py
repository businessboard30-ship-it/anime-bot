import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_connection
from keyboards import get_main_menu
from formatter import format_subscription_status

SUBSCRIPTION_PRICE = 10  # GHS per month
SUBSCRIPTION_PLAN_ID = "ai_features_monthly"

async def handle_subscribe_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription to AI features"""
    user_id = update.effective_user.id
    
    # Check if user already has subscription
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "SELECT subscription_status, subscription_expiry FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    db.close()
    
    if result and result[0] == "active":
        expiry = result[1]
        await update.message.reply_text(
            f"Yo, you already got AI unlocked! 🎮\n\n"
            f"Your subscription expires on: {expiry}\n\n"
            f"Need AI stuff? Hit /ai_recommend or /ai_summary",
            reply_markup=get_main_menu()
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("💳 Pay with Stripe (10 GHS/month)", callback_data="pay_stripe_ai")],
        [InlineKeyboardButton("📲 Pay with Paystack (10 GHS/month)", callback_data="pay_paystack_ai")],
        [InlineKeyboardButton("❌ Nah, I'm good", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "AI Features Subscription 🤖\n\n"
        "Unlock:\n"
        "• Anime recommendations personalized for you\n"
        "• Gen Z AI-powered anime summaries\n"
        "• Priority AI processing\n\n"
        "Only 10 GHS/month! Cancel anytime.\n\n"
        "How you tryna pay?",
        reply_markup=reply_markup
    )


async def handle_ai_recommendation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle AI anime recommendation request"""
    user_id = update.effective_user.id
    
    # Check subscription
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "SELECT subscription_status, subscription_expiry FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    db.close()
    
    if not result or result[0] != "active":
        await update.message.reply_text(
            "Nah fam, this feature requires AI subscription! 🔒\n\n"
            "Subscribe for just 10 GHS/month!\n\n"
            "Hit /subscribe to unlock this",
            reply_markup=get_main_menu()
        )
        return
    
    # Check expiry
    if datetime.now() > datetime.fromisoformat(result[1]):
        await update.message.reply_text(
            "Your subscription expired bruh! 😅\n"
            "Renew it to keep using AI features\n\n"
            "Hit /subscribe to renew!",
            reply_markup=get_main_menu()
        )
        return
    
    await update.message.reply_text(
        "Drop your anime preferences! What kind of anime hits different for you?\n\n"
        "E.g.: Action, romance, comedy vibes idk"
    )
    context.user_data["awaiting_preference"] = True


async def handle_ai_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle AI anime summary request"""
    user_id = update.effective_user.id
    
    # Check subscription
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "SELECT subscription_status, subscription_expiry FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    db.close()
    
    if not result or result[0] != "active":
        await update.message.reply_text(
            "Yo, need subscription for summaries! 🔐\n"
            "Only 10 GHS/month though!\n\n"
            "Hit /subscribe to unlock",
            reply_markup=get_main_menu()
        )
        return
    
    await update.message.reply_text(
        "Search for an anime and I'll give you the gen z summary! 💯"
    )


def activate_subscription(user_id: int, months: int = 1) -> bool:
    """Activate subscription for user"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        expiry = datetime.now() + timedelta(days=30 * months)
        
        cursor.execute(
            """UPDATE users SET subscription_status = ?, subscription_expiry = ? 
               WHERE user_id = ?""",
            ("active", expiry.isoformat(), user_id)
        )
        
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"[v0] Error activating subscription: {e}")
        return False


def deactivate_subscription(user_id: int) -> bool:
    """Deactivate subscription for user"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute(
            """UPDATE users SET subscription_status = ? WHERE user_id = ?""",
            ("inactive", user_id)
        )
        
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"[v0] Error deactivating subscription: {e}")
        return False


def get_active_subscribers() -> List[Dict]:
    """Get all active subscribers for admin"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute(
            """SELECT user_id, username, subscription_expiry FROM users 
               WHERE subscription_status = 'active' 
               ORDER BY subscription_expiry DESC"""
        )
        
        subscribers = []
        for row in cursor.fetchall():
            subscribers.append({
                "user_id": row[0],
                "username": row[1],
                "expiry": row[2]
            })
        
        db.close()
        return subscribers
    except Exception as e:
        print(f"[v0] Error fetching subscribers: {e}")
        return []


def get_subscription_revenue() -> Dict:
    """Get subscription revenue stats for admin"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE subscription_status = 'active'"
        )
        active_count = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE subscription_status = 'expired'"
        )
        expired_count = cursor.fetchone()[0]
        
        monthly_revenue = active_count * SUBSCRIPTION_PRICE
        
        db.close()
        
        return {
            "active": active_count,
            "expired": expired_count,
            "monthly_revenue_ghs": monthly_revenue,
            "price_per_month": SUBSCRIPTION_PRICE
        }
    except Exception as e:
        print(f"[v0] Error calculating revenue: {e}")
        return {}
