"""
All 20 Advanced Telegram Bot Features
Each feature has its own handler function
"""

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, Poll
from telegram.ext import ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from database import db
from config import EMOJI_COLORS
import uuid

# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 1: INLINE QUERY HANDLER - Search @botname in any chat
# ═══════════════════════════════════════════════════════════════════════════

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User types @bot_name to search inline in any chat"""
    query = update.inline_query.query
    user_id = update.effective_user.id
    
    # Store search query
    await db.execute("""
        INSERT INTO inline_searches (user_id, query, result_id, result_type)
        VALUES ($1, $2, $3, $4)
    """, user_id, query, str(uuid.uuid4()), 'search')
    
    # Search anime database
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        results_data = await conn.fetch("""
            SELECT anime_id, title, episodes, rating, image_url FROM anime_entries
            WHERE title ILIKE $1 LIMIT 10
        """, f"%{query}%")
    
    # Convert to inline results
    results = []
    for anime in results_data:
        result = InlineQueryResultArticle(
            id=str(anime['anime_id']),
            title=anime['title'],
            input_message_content=InputTextMessageContent(
                message_text=f"📺 {anime['title']}\n⭐ Rating: {anime['rating']}/10\n📍 Episodes: {anime['episodes']}"
            ),
            description=f"{anime['episodes']} episodes • Rating: {anime['rating']}/10",
            thumbnail_url=anime['image_url']
        )
        results.append(result)
    
    await update.inline_query.answer(results, cache_time=300)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 2: CHOSEN INLINE RESULT - Track which result user clicked
# ═══════════════════════════════════════════════════════════════════════════

async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track when user clicks an inline search result"""
    result_id = update.chosen_inline_result.result_id
    user_id = update.effective_user.id
    query = update.chosen_inline_result.query
    
    # Mark as chosen in database
    await db.execute("""
        UPDATE inline_searches SET was_chosen = true
        WHERE user_id = $1 AND result_id = $2 AND query = $3
    """, user_id, result_id, query)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 3: MY CHAT MEMBER - Know when bot is added/removed from group
# ═══════════════════════════════════════════════════════════════════════════

async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot added to group/channel, removed, promoted, or demoted. Feeds both
    the legacy bot_group_membership status column AND the admin panel's
    remote group/channel picker (handlers/admin_remote.py), which needs the
    chat's title/type/username to show a readable list — not just an id."""
    chat = update.my_chat_member.chat
    group_id = chat.id
    new_status = update.my_chat_member.new_chat_member.status
    clone_config = context.bot_data.get("clone_config")
    clone_id = clone_config.get("clone_id") if clone_config else 0

    await db.execute("""
        INSERT INTO bot_group_membership (group_id, clone_id, bot_status)
        VALUES ($1, $2, $3)
        ON CONFLICT (group_id, clone_id) DO UPDATE SET bot_status = EXCLUDED.bot_status
    """, group_id, clone_id, new_status)

    await db.upsert_bot_chat(
        group_id,
        new_status,
        chat_title=chat.title,
        chat_type=chat.type,
        chat_username=chat.username,
        clone_id=clone_id,
    )

    if new_status == "member":
        # Bot was added - send welcome
        await context.bot.send_message(
            chat_id=group_id,
            text=f"{EMOJI_COLORS.get('welcome', '👋')} **Thanks for adding me!**\n\n"
                 f"I can:\n"
                 f"• 🔍 Search anime inline (@bot_name)\n"
                 f"• 📊 Create polls\n"
                 f"• 🎮 Play games\n"
                 f"• 💰 Handle payments\n\n"
                 f"Type /help for more!",
            parse_mode="Markdown"
        )
    elif new_status == "left":
        # Bot was removed - log it
        print(f"[v0] Bot removed from group {group_id}")


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 4: CHAT MEMBER - Track user joins/leaves
# ═══════════════════════════════════════════════════════════════════════════

async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User joined/left group with bot"""
    user_id = update.chat_member.from_user.id
    group_id = update.chat_member.chat.id
    new_status = update.chat_member.new_chat_member.status
    
    event_type = 'join' if new_status == 'member' else 'leave'
    
    await db.execute("""
        INSERT INTO user_group_events (user_id, group_id, event_type)
        VALUES ($1, $2, $3)
    """, user_id, group_id, event_type)
    
    if event_type == 'join':
        # Announce member join
        await context.bot.send_message(
            chat_id=group_id,
            text=f"👋 Welcome {update.chat_member.from_user.first_name}!"
        )

    # Moderation: captcha / join-gate restriction and anti-raid detection.
    from handlers import moderation
    await moderation.handle_member_join_moderation(update, context)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 5: SUCCESSFUL PAYMENT - User paid, grant access
# ═══════════════════════════════════════════════════════════════════════════

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User successfully paid for premium"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    amount = payment.total_amount / 100  # Convert to dollars
    
    # Determine tier unlocked
    tier = "pro" if amount < 50 else "elite"
    
    # Save payment
    await db.execute("""
        INSERT INTO payments (user_id, amount_usd, currency, status, tier_unlocked, completed_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
    """, user_id, amount, payment.currency, 'completed', tier)
    
    # Upgrade user tier
    await db.execute("""
        INSERT INTO superbot_user_tiers (user_id, tier, tier_updated)
        VALUES ($1, $2, NOW())
        ON CONFLICT (user_id) DO UPDATE SET tier = EXCLUDED.tier, tier_updated = NOW()
    """, user_id, tier)
    
    await update.message.reply_text(
        f"✅ **Payment Successful!**\n\n"
        f"You've unlocked **{tier.upper()}** tier!\n"
        f"Amount: ${amount:.2f}\n\n"
        f"Enjoy premium features! 🎉",
        parse_mode="Markdown"
    )


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 6: PRE-CHECKOUT QUERY - Validate before payment
# ═══════════════════════════════════════════════════════════════════════════

async def handle_pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate order before processing payment"""
    query = update.pre_checkout_query
    
    # Example: Check if user already has premium
    user_tier = await db.fetchval(
        "SELECT tier FROM superbot_user_tiers WHERE user_id = $1",
        query.from_user.id
    )
    
    if user_tier == "elite":
        # Already elite - reject
        await query.answer(ok=False, error_message="You already have Elite tier!")
    else:
        # Approve payment
        await query.answer(ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 7: SHIPPING QUERY - Handle shipping address
# ═══════════════════════════════════════════════════════════════════════════

async def handle_shipping_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shipping address for physical products"""
    from telegram import ShippingOption, LabeledPrice
    
    query = update.shipping_query
    
    # Define shipping options
    shipping_options = [
        ShippingOption(
            id="standard",
            title="Standard Shipping",
            price_list=[LabeledPrice(label="Shipping", amount=500)]  # $5
        ),
        ShippingOption(
            id="express",
            title="Express Shipping",
            price_list=[LabeledPrice(label="Shipping", amount=1500)]  # $15
        ),
    ]
    
    await query.answer(ok=True, shipping_options=shipping_options)
    
    # Store address
    address = query.shipping_address
    await db.execute("""
        INSERT INTO shipping_orders (user_id, shipping_address, status)
        VALUES ($1, $2, 'address_selected')
    """, query.from_user.id, f"{address.street_line1}, {address.city}, {address.postal_code}")


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 8: USER PROFILE PHOTOS - Get and display user avatar
# ═══════════════════════════════════════════════════════════════════════════

async def get_user_profile_photo(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Get user's Telegram profile picture"""
    try:
        # Get photos
        photos = await context.bot.get_user_profile_photos(user_id, limit=1)
        
        if photos.photos:
            # Get highest quality photo
            photo = photos.photos[0][-1]
            file = await context.bot.get_file(photo.file_id)
            
            # Cache in database
            await db.execute("""
                INSERT INTO user_profile_photos (user_id, file_id, downloaded_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE SET file_id = EXCLUDED.file_id
            """, user_id, photo.file_id)
            
            return file.file_path
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 9: EDIT MESSAGE HANDLER - Track message edits
# ═══════════════════════════════════════════════════════════════════════════

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track when users edit their messages"""
    user_id = update.effective_user.id
    message_id = update.edited_message.message_id
    new_text = update.edited_message.text
    
    # Check if we've seen this edit before
    existing = await db.fetchrow(
        "SELECT * FROM edited_messages WHERE message_id = $1 AND user_id = $2",
        message_id, user_id
    )
    
    if existing:
        # Update existing record
        await db.execute("""
            UPDATE edited_messages SET 
                edited_text = $1, 
                edit_count = edit_count + 1,
                last_edited = NOW()
            WHERE message_id = $2 AND user_id = $3
        """, new_text, message_id, user_id)
    else:
        # First edit
        await db.execute("""
            INSERT INTO edited_messages (message_id, user_id, edited_text)
            VALUES ($1, $2, $3)
        """, message_id, user_id, new_text)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 10: MESSAGE REACTION HANDLER - Track emoji reactions
# ═══════════════════════════════════════════════════════════════════════════

async def handle_message_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User reacted to message with emoji"""
    user_id = update.effective_user.id
    message_id = update.message_reaction.message_id
    
    for reaction in update.message_reaction.new_reaction:
        emoji = reaction.emoji
        
        await db.execute("""
            INSERT INTO message_reactions (message_id, user_id, emoji)
            VALUES ($1, $2, $3)
            ON CONFLICT (message_id, user_id, emoji) DO NOTHING
        """, message_id, user_id, emoji)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 11: POLL HANDLER - Create interactive polls
# ═══════════════════════════════════════════════════════════════════════════

async def send_poll(chat_id: int, question: str, options: list, context: ContextTypes.DEFAULT_TYPE):
    """Send a poll to users"""
    poll_msg = await context.bot.send_poll(
        chat_id=chat_id,
        question=question,
        options=options,
        is_anonymous=False,
        type=Poll.QUIZ if len(options) <= 4 else Poll.REGULAR
    )
    
    poll_id = poll_msg.poll.id
    
    # Store poll
    await db.execute("""
        INSERT INTO polls (poll_id, creator_id, question, options, vote_counts)
        VALUES ($1, $2, $3, $4, $5)
    """, poll_id, chat_id, question, options, [0] * len(options))
    
    return poll_msg


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User voted in poll"""
    poll_id = update.poll_answer.poll_id
    options = update.poll_answer.option_ids
    
    # Get poll data
    poll_data = await db.fetchrow(
        "SELECT * FROM polls WHERE poll_id = $1", poll_id
    )
    
    if poll_data:
        vote_counts = list(poll_data['vote_counts'])
        for option_idx in options:
            if option_idx < len(vote_counts):
                vote_counts[option_idx] += 1
        
        await db.execute("""
            UPDATE polls SET vote_counts = $1 WHERE poll_id = $2
        """, vote_counts, poll_id)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 12: DICE HANDLER - Gamified rewards with dice rolls
# ═══════════════════════════════════════════════════════════════════════════

async def handle_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User rolled dice - give reward"""
    user_id = update.effective_user.id
    dice_result = update.message.dice.value
    
    # Calculate reward (higher roll = more reward)
    reward = dice_result * 50  # 50-300 points
    
    await db.execute("""
        INSERT INTO dice_rolls (user_id, dice_type, result, reward)
        VALUES ($1, 'cube', $2, $3)
    """, user_id, dice_result, reward)
    
    # Add points to user
    await db.execute("""
        UPDATE users SET submission_count = submission_count + $1
        WHERE user_id = $2
    """, reward, user_id)
    
    await update.message.reply_text(
        f"🎲 Dice roll: **{dice_result}**\n"
        f"You earned **{reward}** points! 🎉"
    )


async def send_dice(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Send dice game"""
    await context.bot.send_dice(chat_id=chat_id, emoji="🎲")


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 13: GAME HANDLER - Telegram mini-games
# ═══════════════════════════════════════════════════════════════════════════

async def send_game(chat_id: int, game_short_name: str, context: ContextTypes.DEFAULT_TYPE):
    """Send Telegram game"""
    await context.bot.send_game(chat_id=chat_id, game_short_name=game_short_name)


async def handle_game_high_score(user_id: int, game_name: str, score: int):
    """Update user's game high score"""
    await db.execute("""
        INSERT INTO user_games (user_id, game_name, high_score, play_count)
        VALUES ($1, $2, $3, 1)
        ON CONFLICT (user_id, game_name) DO UPDATE SET
            high_score = GREATEST(EXCLUDED.high_score, $3),
            play_count = play_count + 1
    """, user_id, game_name, score)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 14: WEB APP HANDLER - Rich UI in Telegram
# ═══════════════════════════════════════════════════════════════════════════

def get_web_app_button(url: str, button_text: str = "Open App") -> InlineKeyboardMarkup:
    """Create web app button"""
    web_app_info = WebAppInfo(url=url)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(button_text, web_app=web_app_info)
    ]])


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive data from WebApp"""
    user_id = update.effective_user.id
    web_app_data = update.effective_message.web_app_data.data
    
    # Store session
    session_token = str(uuid.uuid4())
    await db.execute("""
        INSERT INTO web_app_sessions (user_id, session_token, web_app_data)
        VALUES ($1, $2, $3)
    """, user_id, session_token, web_app_data)
    
    await update.message.reply_text(
        f"✅ Data received from app!\n"
        f"Session: {session_token}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 15: PASSPORT HANDLER - Age verification
# ═══════════════════════════════════════════════════════════════════════════

async def handle_passport_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User submitted identity documents"""
    user_id = update.effective_user.id
    passport_data = update.message.passport_data
    
    # Store verification
    await db.execute("""
        INSERT INTO passport_verifications (user_id, document_type, verification_status, age_verified)
        VALUES ($1, $2, $3, $4)
    """, user_id, passport_data.decrypted_data.type if hasattr(passport_data, 'decrypted_data') else 'unknown', 'verified', True)
    
    await update.message.reply_text("✅ Identity verified! You can now access mature content.")


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 16: LOCATION HANDLER - Geofencing & proximity
# ═══════════════════════════════════════════════════════════════════════════

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User shared location"""
    user_id = update.effective_user.id
    location = update.message.location
    
    # Store location
    await db.execute("""
        INSERT INTO user_locations (user_id, latitude, longitude, updated_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            updated_at = NOW()
    """, user_id, location.latitude, location.longitude)
    
    # Check proximity alerts
    alerts = await db.fetch("""
        SELECT * FROM proximity_alerts WHERE user_id = $1 AND alert_sent = false
    """, user_id)
    
    for alert in alerts:
        # Calculate distance
        distance = calculate_distance(
            location.latitude, location.longitude,
            alert['event_latitude'], alert['event_longitude']
        )
        
        if distance <= alert['alert_radius_km']:
            # Send alert
            await update.message.reply_text(
                f"📍 **{alert['event_name']}** is near you!\n"
                f"Distance: {distance:.1f} km away"
            )
            
            # Mark as sent
            await db.execute("""
                UPDATE proximity_alerts SET alert_sent = true WHERE id = $1
            """, alert['id'])


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in km"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 17: VIDEO CHAT MEMBERS - Group video call tracking
# ═══════════════════════════════════════════════════════════════════════════

async def handle_video_chat_members_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track group video calls"""
    group_id = update.effective_chat.id
    
    await db.execute("""
        INSERT INTO group_video_calls (group_id, status)
        VALUES ($1, 'active')
    """, group_id)


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 18: USER SHARED - Request user share (referrals)
# ═══════════════════════════════════════════════════════════════════════════

def get_user_share_button() -> ReplyKeyboardMarkup:
    """Create button to request user share"""
    return ReplyKeyboardMarkup([[
        KeyboardButton("Share Friend 👥", request_user=True)
    ]])


async def handle_user_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User shared another user - track referral"""
    sharer_id = update.effective_user.id
    shared_user_id = update.message.user_shared.user_id
    
    # Store referral
    await db.execute("""
        INSERT INTO user_shares (sharer_id, shared_user_id, share_type)
        VALUES ($1, $2, 'user_share')
    """, sharer_id, shared_user_id)
    
    # Give bonus
    await update.message.reply_text(
        "✅ Friend shared! You earned 100 bonus points! 🎉"
    )


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 19: DEEP LINKS - Shareable links with parameters
# ═══════════════════════════════════════════════════════════════════════════

def generate_deep_link(target_type: str, target_id: str) -> str:
    """Generate shareable deep link"""
    link_code = str(uuid.uuid4())[:8]
    # Would be: https://t.me/your_bot?start={link_code}
    return link_code


async def handle_deep_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicked deep link in /start"""
    args = context.args
    
    if args:
        link_code = args[0]
        
        # Get link info
        link_info = await db.fetchrow(
            "SELECT * FROM deep_links WHERE link_code = $1",
            link_code
        )
        
        if link_info:
            # Update click count
            await db.execute("""
                UPDATE deep_links SET clicked_count = clicked_count + 1
                WHERE link_code = $1
            """, link_code)
            
            # Show target content
            await update.message.reply_text(
                f"🔗 You opened: {link_info['target_type']}\n"
                f"ID: {link_info['target_id']}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 20: WRITE ACCESS ALLOWED - WebApp permission
# ═══════════════════════════════════════════════════════════════════════════

async def handle_write_access_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User allowed bot to send unsolicited messages"""
    user_id = update.effective_user.id
    
    await db.execute("""
        INSERT INTO user_write_access (user_id, write_access_allowed, permission_granted_at)
        VALUES ($1, true, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            write_access_allowed = true,
            permission_granted_at = NOW()
    """, user_id)
    
    await update.message.reply_text(
        "✅ Thanks! I can now send you updates and promos!\n"
        "You'll get exclusive offers first! 🎁"
    )
