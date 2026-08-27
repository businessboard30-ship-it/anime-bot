# Quick Start Guide

Get the Anime Bot running in 5 minutes!

## Option 1: Local Testing (Fastest)

```bash
# 1. Clone repository
git clone <your-repo>
cd anime_bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env

# 4. Edit .env with your values:
# - SINOBANED2_BOT_TOKEN (get from @BotFather)
# - ADMIN_ID (your Telegram user ID)

# 5. Run the bot
python main.py
```

Open Telegram, find your bot, and send `/start`!

## Option 2: Railway Deployment (Recommended)

### A. Prepare Code
```bash
# Push to GitHub
git add .
git commit -m "Initial bot setup"
git push origin main
```

### B. Deploy
1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select your repository
4. Add PostgreSQL service
5. Add environment variables (see below)
6. Deploy!

### C. Set Variables in Railway
```
SINOBANED2_BOT_TOKEN=your_bot_token
ADMIN_ID=your_user_id
DATABASE_URL=automatically_set_by_postgres_service
PAYSTACK_SECRET_KEY=your_paystack_key
PAYSTACK_PUBLIC_KEY=your_paystack_key
```

## Getting Your Token

**Telegram Bot Token:**
1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Follow the instructions
5. Copy your token

**Your Admin ID:**
1. Send a message to your bot
2. Use `@userinfobot` in Telegram
3. Copy your user ID

**Paystack Keys (optional, only needed for payments):**
1. Create account at paystack.com
2. Go to Settings → API Keys
3. Copy Secret Key
4. Copy Public Key

## First Commands

Once bot is running:

```
/start          - Show main menu
/admin          - Access admin panel (admin only)
```

## Main Features

- **Trending**: 🔥 Click to see trending anime
- **Latest**: ✨ Newest releases
- **Ongoing**: 🔄 Currently airing
- **Season**: 📅 This season's anime
- **Movies**: 🎬 Anime movies
- **Search**: 🔍 Find any anime
- **Submit**: 📤 Add your favorite anime
- **Clone**: 🤖 Create your own bot (50 GHS)

## Troubleshooting

### Bot not responding?
- Check bot token is correct
- Verify in Railway logs
- Restart the bot

### Database error?
- Check DATABASE_URL is set
- Verify PostgreSQL service is running
- Restart both services

### Payment not working?
- Add Paystack keys to environment
- Test in Paystack sandbox first

## Next: Full Documentation

See `README.md` for complete documentation
See `DEPLOYMENT_GUIDE.md` for detailed deployment steps

---

Happy bot-building! 🎬
