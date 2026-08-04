"""
Games Handler
Trivia and riddle mini-games, ported from SUPER-BOT.
Wins award points through the existing superbot points/leaderboard system.
"""

import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import EMOJI_COLORS
from modules import superbot_adapter

TRIVIA_QUESTIONS = [
    {"q": "Which country won the 2022 FIFA World Cup?", "opts": ["France", "Brazil", "Argentina", "Germany"], "ans": 2},
    {"q": "How many continents are there on Earth?", "opts": ["5", "6", "7", "8"], "ans": 2},
    {"q": "Who holds the record for most Ballon d'Or awards?", "opts": ["Ronaldo", "Messi", "Zidane", "Ronaldinho"], "ans": 1},
    {"q": "Which club has won the most UEFA Champions League titles?", "opts": ["Barcelona", "Bayern Munich", "Real Madrid", "Liverpool"], "ans": 2},
    {"q": "What is the capital of Ghana?", "opts": ["Kumasi", "Accra", "Tamale", "Cape Coast"], "ans": 1},
    {"q": "What does CPU stand for?", "opts": ["Central Power Unit", "Core Processing Unit", "Central Processing Unit", "Computer Power Unit"], "ans": 2},
    {"q": "Which planet is known as the Red Planet?", "opts": ["Venus", "Jupiter", "Mars", "Saturn"], "ans": 2},
    {"q": "Who painted the Mona Lisa?", "opts": ["Michelangelo", "Raphael", "Leonardo da Vinci", "Donatello"], "ans": 2},
    {"q": "What is the largest ocean on Earth?", "opts": ["Atlantic", "Indian", "Arctic", "Pacific"], "ans": 3},
    {"q": "How many sides does a hexagon have?", "opts": ["5", "6", "7", "8"], "ans": 1},
]

RIDDLES = [
    ("I speak without a mouth and hear without ears. I have no body, but come alive with wind. What am I?", "An echo"),
    ("The more you take, the more you leave behind. What am I?", "Footsteps"),
    ("I have cities, but no houses live there. I have mountains, but no trees grow. I have water, but no fish swim. What am I?", "A map"),
    ("What has hands but can't clap?", "A clock"),
    ("I'm light as a feather, but the strongest man can't hold me for more than 5 minutes. What am I?", "Breath"),
]

TRIVIA_WIN_POINTS = 5
SPIN_WIN_POINTS = 10

# Note: SUPER-BOT's original "Lucky Spin" could award a free AI question, tied
# to its own ai_uses counter. This bot gates AI access by subscription instead
# (see handlers/subscription.py), so that prize doesn't map over — it's
# replaced with a points prize so every spin outcome still has real value.
SPIN_PRIZES = [
    ("🎉 Jackpot! You win {pts} bonus points!", True),
    ("🌟 Lucky spin! Try trivia next.", False),
    ("🎰 Almost! Spin again.", False),
    ("💫 Star roller! Try the riddle game.", False),
    ("🏆 Champion! You got bragging rights.", False),
]


def _games_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 TRIVIA", callback_data="g_trivia")],
        [InlineKeyboardButton("🎲 RIDDLE", callback_data="g_riddle")],
        [InlineKeyboardButton("🔢 GUESS THE NUMBER", callback_data="g_guess")],
        [InlineKeyboardButton("🎰 LUCKY SPIN", callback_data="g_spin")],
        [InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="main_menu")],
    ])


async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the games menu (m_games)"""
    query = update.callback_query
    text = "🎮 **Mini-Games**\n\nTest your knowledge and earn points!"
    await query.edit_message_text(text, reply_markup=_games_menu_keyboard(), parse_mode="Markdown")


async def start_trivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a random trivia question (g_trivia)"""
    query = update.callback_query
    q = random.choice(TRIVIA_QUESTIONS)
    context.user_data["trivia"] = q

    opts = [InlineKeyboardButton(f"{'ABCD'[i]}. {o}", callback_data=f"g_ans_{i}")
            for i, o in enumerate(q["opts"])]
    rows = [[opts[0], opts[1]], [opts[2], opts[3]]]
    rows.append([InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_games")])

    await query.edit_message_text(
        f"🧠 *TRIVIA QUIZ*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n*{q['q']}*",
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown"
    )


async def answer_trivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a trivia answer selection (g_ans_N)"""
    query = update.callback_query
    user_id = update.effective_user.id
    ans = int(query.data.split("_")[-1])

    q = context.user_data.get("trivia")
    if not q:
        await query.edit_message_text(
            "Session expired. Try again.",
            reply_markup=_games_menu_keyboard()
        )
        return

    correct = q["ans"]
    if ans == correct:
        await superbot_adapter.add_points(user_id, "trivia_win", TRIVIA_WIN_POINTS)
        await query.edit_message_text(
            f"✅ *CORRECT!* +{TRIVIA_WIN_POINTS} points 🏆\n\n*{q['opts'][correct]}* is right! 🎉",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 NEXT QUESTION", callback_data="g_trivia"),
                InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_games"),
            ]]),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"❌ *WRONG!*\n\nThe correct answer was: *{q['opts'][correct]}*",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 TRY AGAIN", callback_data="g_trivia"),
                InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_games"),
            ]]),
            parse_mode="Markdown"
        )


async def start_riddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a random riddle (g_riddle)"""
    query = update.callback_query
    riddle, answer = random.choice(RIDDLES)
    context.user_data["riddle_ans"] = answer
    context.user_data["mode"] = "riddle"

    await query.edit_message_text(
        f"🎲 *RIDDLE*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n_{riddle}_\n\n_Type your answer!_",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💡 REVEAL ANSWER", callback_data="g_reveal")],
            [InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_games")],
        ]),
        parse_mode="Markdown"
    )


async def reveal_riddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reveal the current riddle's answer (g_reveal)"""
    query = update.callback_query
    ans = context.user_data.get("riddle_ans", "?")
    context.user_data.pop("mode", None)
    await query.edit_message_text(
        f"💡 *ANSWER:* _{ans}_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 NEW RIDDLE", callback_data="g_riddle"),
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_games"),
        ]]),
        parse_mode="Markdown"
    )


async def handle_riddle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a typed riddle answer (mode == 'riddle'), called from the main text dispatcher"""
    user_id = update.effective_user.id
    text = update.message.text
    ans = context.user_data.get("riddle_ans", "")

    if text.lower().strip() in ans.lower():
        await superbot_adapter.add_points(user_id, "riddle_win", TRIVIA_WIN_POINTS)
        context.user_data.pop("mode", None)
        context.user_data.pop("riddle_ans", None)
        await update.message.reply_text(
            f"🎉 *CORRECT!* +{TRIVIA_WIN_POINTS} points 🏆 Well done!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 NEW RIDDLE", callback_data="g_riddle"),
                InlineKeyboardButton("🏠 MENU", callback_data="main_menu"),
            ]])
        )
    else:
        await update.message.reply_text(
            "❌ Not quite! Try again or reveal the answer.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💡 REVEAL", callback_data="g_reveal"),
                InlineKeyboardButton("🔄 NEW RIDDLE", callback_data="g_riddle"),
            ]])
        )


async def start_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a number-guessing game (g_guess)"""
    query = update.callback_query
    n = random.randint(1, 20)
    context.user_data["guess_num"] = n
    context.user_data["guess_tries"] = 0
    context.user_data["mode"] = "guess"

    await query.edit_message_text(
        "🔢 *GUESS THE NUMBER*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "I'm thinking of a number between *1 and 20*.\nType your guess!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_games")
        ]]),
        parse_mode="Markdown"
    )


async def handle_guess_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a typed number guess (mode == 'guess'), called from the main text dispatcher"""
    text = update.message.text
    try:
        guess = int(text)
    except ValueError:
        await update.message.reply_text("⚠️ Please type a number between 1 and 20.")
        return

    n = context.user_data.get("guess_num", 10)
    tries = context.user_data.get("guess_tries", 0) + 1
    context.user_data["guess_tries"] = tries

    if guess == n:
        context.user_data.pop("mode", None)
        context.user_data.pop("guess_num", None)
        context.user_data.pop("guess_tries", None)
        await update.message.reply_text(
            f"🎉 *CORRECT!* The number was *{n}*!\nYou got it in *{tries}* tries!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 PLAY AGAIN", callback_data="g_guess"),
                InlineKeyboardButton("🏠 MENU", callback_data="main_menu"),
            ]])
        )
    elif guess < n:
        await update.message.reply_text(f"📈 Too low! Try higher. (Attempt {tries})")
    else:
        await update.message.reply_text(f"📉 Too high! Try lower. (Attempt {tries})")


async def start_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Spin the prize wheel (g_spin)"""
    query = update.callback_query
    user_id = update.effective_user.id
    prize_text, is_jackpot = random.choice(SPIN_PRIZES)

    if is_jackpot:
        await superbot_adapter.add_points(user_id, "spin_jackpot", SPIN_WIN_POINTS)
        prize_text = prize_text.format(pts=SPIN_WIN_POINTS)

    await query.edit_message_text(
        f"🎰 *LUCKY SPIN*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{prize_text}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 SPIN AGAIN", callback_data="g_spin"),
            InlineKeyboardButton(f"{EMOJI_COLORS.get('back', '⬅️')} Back", callback_data="m_games"),
        ]]),
        parse_mode="Markdown"
    )
