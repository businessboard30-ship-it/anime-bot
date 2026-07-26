# Anime Discovery Bot v1.1.0

Production-ready Telegram bot for anime discovery with AI features, payments, and bot cloning.

**Status:** Ready to Deploy | **Cost:** $0/month | **Revenue:** 600+ GHS/month potential

---

## Quick Start (20 minutes)

### 1. Setup Database (5 min)
```bash
# Go to: https://supabase.com
# Sign up → Create project → Copy connection string
# In SQL Editor: paste docs/setup/01_SUPABASE_SETUP.txt
# Run the SQL migration
```

See detailed guide: `docs/setup/01_SUPABASE_SETUP.txt`

### 2. Create Environment File (1 min)
```bash
cp .env.example .env
# Fill in your credentials:
# - Bot token (from @BotFather)
# - Admin ID (from @userinfobot)
# - DATABASE_URL (from Supabase)
# - Paystack keys (from paystack.com)
```

See all variables: `docs/setup/04_ALL_VARIABLES_EXPLAINED.txt`

### 3. Test Locally (3 min)
```bash
pip install -r requirements.txt
python main.py
# Send /start to your bot in Telegram
```

### 4. Deploy to Vercel (5 min)
```bash
git add . && git commit -m "v1.1.0" && git push
# vercel.com/new → import repo → deploy
```

See detailed guide: `docs/deployment/01_VERCEL_DEPLOYMENT.md`

### 5. Set Webhook (2 min)
```bash
curl -X POST https://api.telegram.org/botYOUR_TOKEN/setWebhook \
  -d url="https://your-project.vercel.app/api/bot"
```

### 6. Done!
Your bot is now live and earning!

---

## Project Structure

```
anime-bot/
├── README.md                 # This file
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
├── Procfile                 # Railway deployment
│
├── main.py                  # Bot entry point
├── config.py                # Configuration
├── database.py              # Database layer
├── anime_service.py         # Anime APIs (AniList + Jikan)
├── groq_service.py          # Groq AI service
├── payments.py              # Payment processing (Paystack + Stripe)
├── formatter.py             # Text formatting
├── keyboards.py             # Telegram buttons/UI
│
├── api/
│   └── bot.py              # Vercel webhook endpoint
│
├── handlers/
│   ├── __init__.py
│   ├── discover.py         # Trending/Latest/Ongoing anime
│   ├── search.py           # Anime search
│   ├── submit.py           # User submissions
│   ├── subscription.py     # AI subscription management
│   ├── admin_panel.py      # Admin dashboard
│   └── clone_bot.py        # Bot cloning feature
│
├── utils/
│   ├── __init__.py
│   ├── validator.py        # Input validation
│   └── rate_limiter.py     # Rate limiting
│
├── sql/
│   └── supabase_migration.sql  # Database schema
│
├── docs/
│   ├── setup/
│   │   ├── 01_SUPABASE_SETUP.txt
│   │   ├── 02_SUPABASE_QUICK_START.txt
│   │   ├── 03_ENVIRONMENT_SETUP.md
│   │   └── 04_ALL_VARIABLES_EXPLAINED.txt
│   │
│   ├── deployment/
│   │   ├── 01_VERCEL_DEPLOYMENT.md
│   │   ├── 02_QUICK_START.txt
│   │   ├── 03_CHECKLIST.md
│   │   ├── 04_DETAILED_GUIDE.md
│   │   └── 05_RAILWAY_ALTERNATIVE.md
│   │
│   ├── features/
│   │   ├── 01_NEW_FEATURES_v1.1.0.md
│   │   ├── 02_UPGRADE_SUMMARY.md
│   │   └── 03_ARCHITECTURE.md
│   │
│   └── api/
│       └── 01_PROJECT_OVERVIEW.txt
│
└── archive/
    └── old_docs/           # Historical documentation
```

---

## Features

### Core
- **Anime Discovery** - Trending, Latest, Ongoing, Seasonal anime
- **Search** - Find any anime by title
- **Categories** - Browse by genre
- **User Submissions** - Community contributions with admin review

### Premium (10 GHS/month)
- **AI Recommendations** - Groq AI suggests anime
- **AI Summaries** - Get episode descriptions

### Monetization
- **Bot Cloning** - 50 GHS per clone
- **Commission Tracking** - 10% on clone bot sales
- **Subscriptions** - Monthly recurring revenue

### Admin
- **Revenue Dashboard** - Track earnings
- **Subscriber Management** - View active users
- **Commission Tracking** - Monitor clone bot sales
- **Analytics** - User statistics

---

## Technology Stack

- **Language:** Python 3.9+
- **Bot Framework:** python-telegram-bot
- **Database:** PostgreSQL (Supabase)
- **AI:** Groq API
- **Payments:** Paystack + Stripe
- **Hosting:** Vercel (serverless)
- **APIs:** AniList (GraphQL) + Jikan (REST)

---

## Environment Variables

**Required (4):**
- `SINOBANED2_BOT_TOKEN` - Telegram bot token
- `ADMIN_ID` - Your Telegram user ID
- `DATABASE_URL` - PostgreSQL connection string
- `GROQ_API_KEY` - Groq API key

**Payments (4):**
- `PAYSTACK_SECRET_KEY` - Paystack live secret
- `PAYSTACK_PUBLIC_KEY` - Paystack live public
- `STRIPE_SECRET_KEY` - Stripe secret (optional)
- `STRIPE_PUBLIC_KEY` - Stripe public (optional)

**Configuration:**
- `NODE_ENV` - Set to "production"
- `LOG_LEVEL` - Set to "INFO"
- `TELEGRAM_WEBHOOK_URL` - Vercel webhook URL

See full details: `docs/setup/04_ALL_VARIABLES_EXPLAINED.txt`

---

## Revenue Potential

**Subscriptions:** 10 GHS/month × 50 users = 500 GHS/month

**Bot Clones:** 50 GHS each × 10 clones = 500 GHS

**Commissions:** 10% of clone bot sales ≈ 100+ GHS/month

**First Month:** 800+ GHS | **Recurring:** 600+ GHS/month

**Cost to Run:** $0/month (all free services)

---

## Database Schema

10 tables created automatically:
- `users` - User profiles & subscriptions
- `anime_entries` - Anime database
- `submissions` - User contributions
- `cloned_bots` - Bot instances
- `payment_logs` - All transactions
- `commission_tracking` - Clone sales
- `subscription_payments` - Monthly subs
- `ai_usage_tracking` - AI analytics
- `bot_analytics` - Bot metrics
- `admin_logs` - Admin actions

Run `sql/supabase_migration.sql` to create all tables.

---

## Deployment Options

### Option 1: Vercel (Recommended - Free)
- Free forever
- Auto-scaling
- Webhook-based
- See: `docs/deployment/01_VERCEL_DEPLOYMENT.md`

### Option 2: Railway
- Free tier available
- Polling-based
- Always-on
- See: `docs/deployment/05_RAILWAY_ALTERNATIVE.md`

### Option 3: Local/VPS
- Run on your machine
- Development/testing
- Full control

---

## Getting Help

**Documentation by topic:**

| Topic | File |
|-------|------|
| Setup Supabase | `docs/setup/01_SUPABASE_SETUP.txt` |
| Environment vars | `docs/setup/04_ALL_VARIABLES_EXPLAINED.txt` |
| Deploy to Vercel | `docs/deployment/01_VERCEL_DEPLOYMENT.md` |
| Check before launch | `docs/deployment/03_CHECKLIST.md` |
| Features overview | `docs/features/01_NEW_FEATURES_v1.1.0.md` |
| Architecture | `docs/features/03_ARCHITECTURE.md` |

**Old documentation:** See `archive/` folder

---

## License

MIT

---

## Current Status

✅ Bot code complete and tested  
✅ Database schema ready  
✅ Payments integrated  
✅ AI features configured  
✅ Admin dashboard built  
✅ Documentation complete  
⏳ Ready to deploy  

**Next Step:** Follow `docs/setup/01_SUPABASE_SETUP.txt` to set up your database!
