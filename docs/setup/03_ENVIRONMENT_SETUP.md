# Environment Variables Setup Guide

Complete guide to getting all environment variables needed for your anime bot.

## Quick Summary - What You Need

| Variable | Required? | Cost | Time | Where |
|----------|-----------|------|------|-------|
| `SINOBANED2_BOT_TOKEN` | YES | FREE | 2 min | @BotFather |
| `ADMIN_ID` | YES | FREE | 1 min | @userinfobot |
| `DATABASE_URL` | YES | FREE | 5 min | Supabase |
| `GROQ_API_KEY` | YES | FREE | 3 min | console.groq.com |
| `PAYSTACK_*` | Optional | FREE | 5 min | paystack.com |
| `STRIPE_*` | Optional | FREE | 5 min | stripe.com |
| `TELEGRAM_WEBHOOK_URL` | For Vercel | - | Auto | Vercel |

**Total Time: ~20 minutes**

---

## Step-by-Step Setup

### 1. Telegram Bot Token (2 minutes)

**What it is**: Authentication for your bot

**Get it:**
1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Choose a name (e.g., "My Anime Bot")
5. Choose a username (must end with 'bot', e.g., 'my_anime_bot')
6. Copy the token you receive

**Result**: Token looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

**In .env:**
```
SINOBANED2_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

---

### 2. Your Admin ID (1 minute)

**What it is**: Your Telegram user ID (for admin panel)

**Get it:**
1. Open Telegram
2. Search for `@userinfobot`
3. Send any message
4. Copy the number under "Id"

**Result**: ID is just a number like `123456789`

**In .env:**
```
ADMIN_ID=123456789
```

---

### 3. Database (PostgreSQL - 5 minutes)

**What it is**: Where all bot data is stored

**Option A: Supabase (Recommended - FREE)**

1. Go to https://supabase.com
2. Click "Sign Up"
3. Login with GitHub
4. Create new project
5. Wait for it to be created (1-2 min)
6. Go to Settings → Database
7. Copy "Connection string" (URI format)
8. Replace password with your password from Setup tab

**Result**: Looks like:
```
postgresql://postgres:YourPassword@db.supabase.co:5432/postgres
```

**In .env:**
```
DATABASE_URL=postgresql://postgres:YourPassword@db.supabase.co:5432/postgres
```

**Option B: Railway (Alternative)**

1. Go to https://railway.app
2. Create account with GitHub
3. New Project → PostgreSQL
4. Copy "DATABASE_URL"
5. Done!

**In .env:**
```
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

---

### 4. Groq AI (3 minutes)

**What it is**: Free AI for anime recommendations

**Get it:**
1. Go to https://console.groq.com
2. Sign up
3. Go to API Keys
4. Create new key
5. Copy it

**Result**: Looks like `gsk_abcdef123456...`

**In .env:**
```
GROQ_API_KEY=gsk_abcdef123456...
```

---

### 5. Paystack (5 minutes) - For Bot Clones

**What it is**: Payment processing for 50 GHS bot clones

**Get it:**
1. Go to https://paystack.com
2. Create business account
3. Verify email
4. Go to Settings → API Keys & Webhooks
5. Copy both Secret and Public keys

**Result:**
- Secret: `sk_live_abcdef...`
- Public: `pk_live_abcdef...`

**In .env:**
```
PAYSTACK_SECRET_KEY=sk_live_abcdef...
PAYSTACK_PUBLIC_KEY=pk_live_abcdef...
```

---

### 6. Stripe (5 minutes) - For Clone Commissions

**What it is**: Payment processing for cloned bot sales + 10% commissions

**Get it:**
1. Go to https://stripe.com
2. Create account
3. Go to Developers → API Keys
4. Copy Secret and Publishable keys

**Result:**
- Secret: `sk_test_abcdef...` (or `sk_live_...` for production)
- Public: `pk_test_abcdef...` (or `pk_live_...` for production)

**In .env:**
```
STRIPE_SECRET_KEY=sk_test_abcdef...
STRIPE_PUBLIC_KEY=pk_test_abcdef...
```

---

### 7. Vercel Webhook URL (Auto-generated)

**What it is**: URL where Telegram sends updates to your bot

**Get it:**
1. Deploy to Vercel (see VERCEL_DEPLOYMENT.md)
2. Copy your project URL: `https://your-project.vercel.app`
3. Append `/api/bot`: `https://your-project.vercel.app/api/bot`

**In .env:**
```
TELEGRAM_WEBHOOK_URL=https://your-project.vercel.app/api/bot
```

---

## Complete .env File Example

```env
# TELEGRAM
SINOBANED2_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789
TELEGRAM_WEBHOOK_URL=https://my-anime-bot.vercel.app/api/bot

# DATABASE
DATABASE_URL=postgresql://postgres:YourPassword@db.supabase.co:5432/postgres

# AI
GROQ_API_KEY=gsk_abcdef123456...

# PAYMENTS
PAYSTACK_SECRET_KEY=sk_live_abcdef...
PAYSTACK_PUBLIC_KEY=pk_live_abcdef...
STRIPE_SECRET_KEY=sk_test_abcdef...
STRIPE_PUBLIC_KEY=pk_test_abcdef...

# VERCEL
NODE_ENV=production
VERCEL_ENV=production
VERCEL_URL=my-anime-bot.vercel.app
```

---

## Where to Put .env File

### Local Testing
```
your-project/
├── .env
├── main.py
├── config.py
└── ...
```

### Vercel Deployment

In Vercel Dashboard:
1. Go to your project
2. Settings → Environment Variables
3. Add each variable
4. Deploy

---

## Verification Checklist

After setting up all variables:

- [ ] Telegram bot token works (try `/start` in Telegram)
- [ ] Admin ID is correct (you should see admin commands)
- [ ] Database connected (bot saves user data)
- [ ] Groq API works (AI features respond)
- [ ] Paystack keys work (bot clone option appears)
- [ ] Stripe keys work (commission tracking works)
- [ ] Webhook URL correct (bot receives messages on Vercel)

---

## Common Issues

**"Bot not responding"**
- Check `SINOBANED2_BOT_TOKEN` is correct
- Check webhook URL is set if using Vercel

**"Database connection failed"**
- Check `DATABASE_URL` is correct
- Add your IP to Supabase whitelist (if needed)
- Test connection with `psql` command

**"AI features not working"**
- Check `GROQ_API_KEY` is set
- Verify Groq API is active in console.groq.com

**"Payment buttons not showing"**
- Check `PAYSTACK_*` keys are set
- Verify Paystack account is verified

---

## Security Notes

- Never share your .env file
- Never commit .env to Git (it's in .gitignore)
- Regenerate keys if you think they're exposed
- Use environment variable names as-is (they're configured in code)

---

## Next Steps

After setting up all variables:

1. **Local Testing**: `python main.py`
2. **Deploy to Vercel**: Follow VERCEL_DEPLOYMENT.md
3. **Test in Telegram**: Send `/start` to your bot
4. **Monitor**: Check admin dashboard at `/admin`

Ready? Let's deploy! 🚀
