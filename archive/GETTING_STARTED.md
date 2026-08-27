# Getting Started - Anime Discovery Bot

Welcome! This guide will get your bot up and running in minutes.

## What You're Building

A powerful Telegram bot that:
- Discovers anime from trending to obscure
- Lets users submit their favorite anime
- Has an admin review system
- Allows users to clone the bot (50 GHS via Paystack)
- Beautiful organized UI with animated buttons

## Quick Decision Tree

### "I want to test locally first"
→ Go to **Local Setup** (5 min)

### "I want to deploy to production immediately"
→ Go to **Railway Deployment** (10 min)

### "I want detailed step-by-step setup"
→ Read `INSTALLATION.md` (20 min)

---

## Local Setup (5 minutes)

### 1. Get Prerequisites

You need:
- Python 3.9+ installed
- A Telegram bot token (from @BotFather)
- Your Telegram user ID

**Get Bot Token:**
1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Choose name and username
5. Copy the token given

**Get Your ID:**
1. Search for `@userinfobot` on Telegram
2. Send any message
3. It shows your User ID

### 2. Download & Setup

```bash
# Clone or download the code
git clone <your-repo-url>
cd anime_bot

# Create virtual environment
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 3. Configure

Edit `.env`:
```
SINOBANED2_BOT_TOKEN=paste_your_bot_token_here
ADMIN_ID=paste_your_user_id_here
DATABASE_URL=sqlite:///anime_bot.db
PAYSTACK_SECRET_KEY=
PAYSTACK_PUBLIC_KEY=
```

(Leave Paystack keys empty for now - only needed for payments)

### 4. Run

```bash
python main.py
```

You should see:
```
[v0] Starting Anime Bot...
[v0] Bot is polling...
```

### 5. Test

Open Telegram, find your bot, send `/start`!

---

## Railway Deployment (10 minutes)

### Prerequisites
- GitHub account
- Code pushed to GitHub
- Railway.app account (free)

### Step 1: Prepare

```bash
git add .
git commit -m "Anime bot ready"
git push origin main
```

### Step 2: Deploy on Railway

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Choose your anime-bot repository
5. Click "Deploy"

Railway will:
- Detect it's Python
- Install dependencies
- Start the bot automatically

### Step 3: Add Database

1. In Railway dashboard, click "Add Service"
2. Select "PostgreSQL"
3. PostgreSQL is created automatically

### Step 4: Set Variables

In Railway dashboard → Variables:
```
SINOBANED2_BOT_TOKEN=your_token
ADMIN_ID=your_id
PAYSTACK_SECRET_KEY=key
PAYSTACK_PUBLIC_KEY=key
```

(DATABASE_URL is auto-set by PostgreSQL)

### Step 5: Done!

Your bot is now live! Test in Telegram: send `/start`

---

## Feature Overview

### Main Menu Buttons

When you open the bot, you see:

```
🔥 Trending     ✨ Latest
🔄 Ongoing      📅 Season
🎬 Movies       🔍 Search
📚 Categories   📤 Submit
🤖 Clone Bot
```

### What Each Does

**Trending** - Most popular anime now
**Latest** - New releases this week
**Ongoing** - Currently airing series
**Season** - This season's anime
**Movies** - Anime movies only
**Search** - Find any anime
**Categories** - Browse by genre
**Submit** - Add your favorite anime
**Clone Bot** - Create your own bot

---

## Admin Features

### Access Admin Panel

Send `/admin` command (admin only)

You can:
- Review pending anime submissions
- Approve or reject them
- See submission stats
- Manage cloned bot instances

### Review Submissions

1. Send `/admin`
2. Click "Review Submissions"
3. See user-submitted anime
4. Approve ✅ or Reject ❌

---

## Clone Bot Feature (50 GHS)

Users can create their own bot instance!

### How It Works

1. User clicks "Clone Bot"
2. Sees feature info
3. Pays 50 GHS via Paystack
4. Customizes bot:
   - Bot name
   - Webhook URL (where submissions go)
   - Branding description
   - Service categories
5. Gets unique bot token
6. Bot is ready to use!

---

## Customization

### Change Bot Colors

Edit `config.py`:
```python
EMOJI_COLORS = {
    "trending": "🔥",
    "latest": "✨",
    "ongoing": "🔄",
    "season": "📅",
    "movies": "🎬",
    "search": "🔍",
    "submit": "📤",
    "clone": "🤖",
}
```

### Change Clone Price

In `config.py`:
```python
CLONE_BOT_FEE_GHS = 50  # Change this number
```

### Add More Anime Categories

Edit `handlers/discover.py` and add new queries

---

## Common Issues

### "Bot not responding"
- Check bot is running
- Verify token in .env
- Restart the bot

### "Database error"
- Delete `anime_bot.db` (recreates on restart)
- For Railway: check PostgreSQL is running

### "Payment not working"
- Add Paystack keys to .env
- Use sandbox keys first for testing
- Verify Paystack account is verified

### "Anime not loading"
- Check internet connection
- AniList API might be down
- Try different search term

---

## Next Steps

1. **Test Locally** → Run `python main.py`
2. **Deploy** → Push to Railway
3. **Customize** → Edit `config.py`
4. **Monitor** → Check logs regularly
5. **Scale** → Upgrade Railway plan if needed

---

## Documentation Map

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **QUICKSTART.md** | 5-min setup | 5 min |
| **INSTALLATION.md** | Detailed setup | 20 min |
| **DEPLOYMENT_GUIDE.md** | Railway setup | 15 min |
| **README.md** | Full docs | 30 min |
| **PROJECT_SUMMARY.md** | Technical overview | 10 min |

---

## Key Files Explained

| File | Purpose |
|------|---------|
| `main.py` | Bot entry point |
| `config.py` | All settings |
| `database.py` | Data storage |
| `anime_service.py` | Anime APIs |
| `keyboards.py` | Button layouts |
| `handlers/*.py` | Bot features |
| `.env` | Your secrets |

---

## Support Resources

- **Need help?** Check the file name in error message
- **Want to understand code?** Each file has comments
- **Need API docs?** See links in README.md
- **Having issues?** Check troubleshooting sections

---

## You're All Set! 🚀

Your anime bot is ready!

**Next**: Send your bot `/start` command and explore!

---

**Questions?** Read the docs or check the code comments!
