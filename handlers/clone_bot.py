from telegram import Update
from telegram.ext import ContextTypes
import secrets

from database import db
from keyboards import keyboard_gen
from formatter import AnimeFormatter
from payments import paystack
from config import EMOJI_COLORS, CLONE_BOT_FEE_GHS

async def start_clone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start bot cloning process"""
    query = update.callback_query
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Show clone info
    clone_info = AnimeFormatter.format_clone_info()
    
    await query.edit_message_text(
        clone_info,
        reply_markup=keyboard_gen.clone_payment_keyboard(CLONE_BOT_FEE_GHS),
        parse_mode="Markdown"
    )
    
    context.user_data["clone_step"] = "awaiting_payment"

async def handle_payment_initiation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initialize Paystack payment"""
    query = update.callback_query
    user_id = update.effective_user.id
    user = update.effective_user
    email = f"user_{user_id}@animebot.local"  # Fallback email
    
    if query.data == "paystack_checkout":
        # Initialize payment
        payment_link = paystack.create_payment_link(
            email,
            CLONE_BOT_FEE_GHS,
            user_id,
            f"AnimeBotClone_{user_id}"
        )
        
        if payment_link:
            payment_text = f"""
{EMOJI_COLORS['success']} **Payment Ready**

Click the link below to pay GHS {CLONE_BOT_FEE_GHS}.00 via Paystack:

[Pay Now]({payment_link})

After payment, your bot will be set up automatically!
"""
            
            await query.edit_message_text(
                payment_text,
                reply_markup=keyboard_gen.main_menu(),
                parse_mode="Markdown"
            )
            
            context.user_data["clone_payment_pending"] = True
        else:
            await query.answer("Failed to initialize payment. Please try again.", show_alert=True)

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify payment and create cloned bot"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    reference = context.user_data.get("payment_reference")
    
    if not reference:
        await query.answer("Payment reference not found", show_alert=True)
        return
    
    # Verify with Paystack
    result = paystack.verify_payment(reference)
    
    if result.get("status") == "success":
        # Payment successful - proceed to customization
        await query.edit_message_text(
            f"{EMOJI_COLORS['success']} **Payment Successful!**\n\n"
            f"Your bot clone is being set up. Let's customize it!",
            reply_markup=keyboard_gen.clone_customization_keyboard(),
            parse_mode="Markdown"
        )
        
        context.user_data["clone_step"] = "customizing"
        context.user_data["payment_status"] = "success"
    else:
        await query.edit_message_text(
            f"{EMOJI_COLORS['error']} Payment verification failed. Please try again.",
            reply_markup=keyboard_gen.main_menu()
        )

async def handle_customization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle clone customization steps"""
    query = update.callback_query
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "customize_name":
        context.user_data["customize_step"] = "awaiting_name"
        await query.edit_message_text(
            f"{EMOJI_COLORS['submit']} What name would you like for your bot?\n\n"
            f"(e.g., 'MyAnimeBot', 'NarutoFan_Bot')"
        )
    
    elif callback_data == "customize_webhook":
        context.user_data["customize_step"] = "awaiting_webhook"
        await query.edit_message_text(
            f"{EMOJI_COLORS['submit']} What's your webhook URL?\n\n"
            f"(This is where user submissions will be sent)"
        )
    
    elif callback_data == "customize_branding":
        context.user_data["customize_step"] = "awaiting_branding"
        await query.edit_message_text(
            f"{EMOJI_COLORS['submit']} Describe your bot's branding/theme:\n\n"
            f"(e.g., 'Anime only', 'Manga focused', 'All genres')"
        )
    
    elif callback_data == "customize_categories":
        context.user_data["customize_step"] = "awaiting_categories"
        await query.edit_message_text(
            f"{EMOJI_COLORS['submit']} What service categories?\n\n"
            f"(comma separated, e.g., 'Reviews, Recommendations, News')"
        )
    
    elif callback_data == "finalize_clone":
        await finalize_clone(update, context)

async def handle_customization_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle customization input from messages"""
    text = update.message.text
    customize_step = context.user_data.get("customize_step")
    user_id = update.effective_user.id
    
    if customize_step == "awaiting_name":
        context.user_data["clone_name"] = text
        context.user_data["customize_step"] = None
        await update.message.reply_text(
            f"{EMOJI_COLORS['success']} Bot name set to '{text}'\n\n"
            f"What's next?"
        )
    
    elif customize_step == "awaiting_webhook":
        context.user_data["clone_webhook"] = text
        context.user_data["customize_step"] = None
        await update.message.reply_text(
            f"{EMOJI_COLORS['success']} Webhook set to '{text}'\n\n"
            f"What's next?"
        )
    
    elif customize_step == "awaiting_branding":
        context.user_data["clone_branding"] = text
        context.user_data["customize_step"] = None
        await update.message.reply_text(
            f"{EMOJI_COLORS['success']} Branding set to '{text}'\n\n"
            f"What's next?"
        )
    
    elif customize_step == "awaiting_categories":
        context.user_data["clone_categories"] = text
        context.user_data["customize_step"] = None
        await update.message.reply_text(
            f"{EMOJI_COLORS['success']} Categories set to '{text}'\n\n"
            f"What's next?"
        )

async def finalize_clone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create the cloned bot"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Generate unique bot token
    bot_token = f"{user_id}_{secrets.token_hex(16)}"
    
    # Prepare custom data
    custom_data = {
        "name": context.user_data.get("clone_name", f"AnimeBotClone_{user_id}"),
        "webhook_url": context.user_data.get("clone_webhook", ""),
        "branding": context.user_data.get("clone_branding", ""),
        "categories": context.user_data.get("clone_categories", "")
    }
    
    # Store in database
    clone_id = await db.add_cloned_bot(
        user_id,
        custom_data.get("name"),
        bot_token,
        custom_data.get("webhook_url"),
        custom_data
    )
    
    # Show success message
    success_text = f"""
{EMOJI_COLORS['success']} **Your Bot is Ready!**

**Bot Name:** {custom_data.get('name')}
**Bot Token:** `{bot_token}`
**Status:** Active

Your cloned bot has all the features of the main bot and is ready to use!

Share your bot with others and start managing anime!
"""
    
    await query.edit_message_text(
        success_text,
        reply_markup=keyboard_gen.main_menu(),
        parse_mode="Markdown"
    )
    
    # Reset clone context
    context.user_data["clone_step"] = None
    context.user_data["payment_status"] = None
    context.user_data.pop("clone_name", None)
    context.user_data.pop("clone_webhook", None)
    context.user_data.pop("clone_branding", None)
    context.user_data.pop("clone_categories", None)
