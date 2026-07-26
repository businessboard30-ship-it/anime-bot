# Installation & Setup Guide

Complete guide to install and run the Anime Discovery Bot

## Table of Contents
1. Prerequisites
2. Local Installation
3. Configuration
4. Running the Bot
5. Railway Deployment
6. Troubleshooting

## Prerequisites

- Python 3.9 or higher
- pip or poetry
- Git
- Telegram account
- (Optional) Paystack account for payments

### Check Python Version
```bash
python --version
# Should output Python 3.9.x or higher
```

## Local Installation

### Step 1: Clone Repository

```bash
git clone <your-repository-url>
cd anime_bot
```

### Step 2: Create Virtual Environment

**On macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- python-telegram-bot (20.0+)
- aiohttp & httpx (async HTTP)
- aiosqlite (SQLite database)
- python-dotenv (environment variables)
- requests (HTTP requests)
- paystack-python (Paystack integration)

### Step 4: Create Environment File

```bash
cp .env.example .env
```

Then edit `.env` with your configuration (see Configuration section below).

## Configuration

### Get Telegram Bot Token

1. Open Telegram app
2. Search for `@BotFather`
3. Send `/newbot`
4. Follow the instructions:
   - Choose a display name (e.g., "My Anime Bot")
   - Choose a username (e.g., "my_anime_bot")
5. BotFather will send you a token that looks like:
   ```
   123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ```
6. Copy this token to `SINOBANED2_BOT_TOKEN` in `.env`

### Get Your Admin ID

**Method 1: Using @userinfobot**
1. Open Telegram
2. Search for `@userinfobot`
3. Send `/start`
4. The bot shows your User ID
5. Copy it to `ADMIN_ID` in `.env`

**Method 2: From Bot Logs**
1. Run the bot locally
2. Send it a message
3. Check the console output for your user ID

### Configure Database

**For Local Testing (SQLite - Default):**
```
DATABASE_URL=sqlite:///anime_bot.db
```
This will create a local database file. No setup needed!

**For Production (PostgreSQL):**
```
DATABASE_URL=postgresql://username:password@localhost:5432/anime_db
```

Or use a managed service like:
- Railway.app (recommended)
- Heroku Postgres
- AWS RDS
- Supabase

### Configure Paystack (Optional)

Only needed if you want the bot cloning feature with payments.

1. Create account at https://paystack.com
2. Go to Settings → API Keys & Webhooks
3. You'll see:
   - Secret Key (starts with `sk_`)
   - Public Key (starts with `pk_`)
4. Copy to `.env`:
   ```
   PAYSTACK_SECRET_KEY=sk_live_xxxxxxxxxxxx
   PAYSTACK_PUBLIC_KEY=pk_live_xxxxxxxxxxxx
   ```

### Final .env File

```
# Telegram
SINOBANED2_BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_user_id_here

# Database (local SQLite for testing)
DATABASE_URL=sqlite:///anime_bot.db

# Payment (optional, only for clone feature)
PAYSTACK_SECRET_KEY=sk_live_xxxx
PAYSTACK_PUBLIC_KEY=pk_live_xxxx
```

## Running the Bot

### Local Testing

```bash
# Make sure virtual environment is activated
python main.py
```

You should see:
```
[v0] Starting Anime Bot...
[v0] Bot is polling...
```

### Test in Telegram

1. Open Telegram
2. Search for your bot username (e.g., `@my_anime_bot`)
3. Send `/start` command
4. You should see the main menu!

### Test Features

Try each feature:
- Click "Trending" to see trending anime
- Click "Search" and search for an anime
- Click "Submit" to submit an anime
- Click "Clone Bot" to see payment flow
- (Admin only) Click "Admin Panel" to review submissions

### Stop the Bot

Press `Ctrl+C` in the terminal

## Railway Deployment

### Prerequisites
- GitHub account with repository pushed
- Railway.app account

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Initial anime bot setup"
git push origin main
```

### Step 2: Create Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Connect GitHub (if first time)
5. Select your repository
6. Railway auto-detects Python project
7. Deployment starts automatically

### Step 3: Add PostgreSQL

1. In Railway dashboard, click "Add Service"
2. Select "PostgreSQL"
3. A database instance is created
4. Connection URL is automatically added

### Step 4: Configure Environment Variables

In Railway dashboard, go to "Variables" and add:

```
SINOBANED2_BOT_TOKEN=your_bot_token
ADMIN_ID=your_user_id
PAYSTACK_SECRET_KEY=your_secret_key
PAYSTACK_PUBLIC_KEY=your_public_key
```

Note: `DATABASE_URL` is automatically set by PostgreSQL service.

### Step 5: Monitor Deployment

1. Go to "Deployments" tab
2. Wait for deployment status to turn green
3. Check logs for errors
4. Should see: `[v0] Bot is polling...`

### Step 6: Verify

1. Open Telegram
2. Send `/start` to your bot
3. You should see main menu

## Troubleshooting

### "Bot token not found"
**Error**: `TOKEN not found in environment`

**Solution**:
1. Check `.env` file exists
2. Verify `SINOBANED2_BOT_TOKEN` is set
3. Make sure .env file is in project root

### "Bot not responding"
**Error**: No reply when sending messages

**Solution**:
1. Check bot is running: `python main.py`
2. Verify token is correct
3. Check console for errors
4. Try restarting the bot

### "Database connection error"
**Error**: `Can't connect to database` or SQL errors

**Solution for SQLite**:
1. Delete `anime_bot.db` file
2. Restart bot (it recreates the database)

**Solution for PostgreSQL**:
1. Verify `DATABASE_URL` is correct
2. Check PostgreSQL service is running
3. Test connection string manually

### "Anime not loading"
**Error**: "No results found" or loading hangs

**Solution**:
1. Check internet connection
2. Verify AniList API is online: https://anilist.co
3. Check rate limits (max 50 requests/hour)
4. Try searching for a different anime
5. Check console for API errors

### "Payment button not working"
**Error**: Payment link doesn't open

**Solution**:
1. Check Paystack keys are correct
2. Verify Paystack account is verified
3. Test in sandbox mode first
4. Check internet connection

### "Permission denied" on Linux
**Error**: `Permission denied: 'anime_bot.db'`

**Solution**:
```bash
chmod 755 anime_bot.db
chmod 755 .
```

## Next Steps

1. **Read README.md** for feature overview
2. **Read QUICKSTART.md** for quick reference
3. **Read DEPLOYMENT_GUIDE.md** for production deployment
4. **Configure Admin Panel** for content moderation
5. **Customize Features** as needed

## Support & Resources

- Python Telegram Bot: https://python-telegram-bot.readthedocs.io
- AniList API: https://anilist.gitbook.io/anilist-apiv2-docs
- Railway Docs: https://docs.railway.app
- Paystack Docs: https://paystack.com/developers

## Common Commands for Development

```bash
# View virtual environment status
which python

# Exit virtual environment
deactivate

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# View bot logs
tail -f anime_bot.log

# Connect to SQLite database
sqlite3 anime_bot.db

# Show database schema
.schema
```

---

**Installation Complete!** 🎉

Your anime bot is ready to use. Enjoy discovering anime!
