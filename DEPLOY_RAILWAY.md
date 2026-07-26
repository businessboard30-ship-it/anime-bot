# Deploy Your Anime Bot to Railway

Railway is the best platform for Python Telegram bots. It's simple, fast, and cheap.

## Prerequisites

You need:
- Bot Token (from @BotFather)
- Admin ID (your Telegram user ID)
- Paystack Keys (from paystack.com)
- Database ready (Supabase)

## Step 1: Create Railway Account (2 minutes)

1. Go to https://railway.app
2. Click "Start Now"
3. Sign up with GitHub (easiest)
4. Authorize Railway to access your GitHub

## Step 2: Push to GitHub (5 minutes)

If you haven't already:

```bash
cd /your/project
git init
git add .
git commit -m "Anime bot v1.1.0 ready for deployment"
git remote add origin https://github.com/YOUR_USERNAME/anime-bot.git
git push -u origin main
```

## Step 3: Create Railway Project (3 minutes)

1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `anime-bot` repository
5. Click "Deploy Now"

Railway will:
- Install dependencies from `requirements.txt`
- Run your bot using `Procfile`
- Keep it running 24/7

## Step 4: Add Environment Variables (3 minutes)

In Railway dashboard:

1. Your project → Variables
2. Add these variables:

```
SINOBANED2_BOT_TOKEN=[YOUR_BOT_TOKEN_FROM_BOTFATHER]
ADMIN_ID=[YOUR_TELEGRAM_USER_ID]
PAYSTACK_SECRET_KEY=[YOUR_PAYSTACK_SECRET_KEY]
PAYSTACK_PUBLIC_KEY=[YOUR_PAYSTACK_PUBLIC_KEY]
DATABASE_URL=[YOUR_SUPABASE_CONNECTION_STRING]
GROQ_API_KEY=[optional_if_you_have_it]
```

### Getting DATABASE_URL from Supabase

1. Supabase Dashboard → Your Project
2. Settings → Database
3. Copy "Connection string" (PostgreSQL)
4. Paste it as `DATABASE_URL`

## Step 5: Verify Deployment (2 minutes)

In Railway:

1. Go to Logs tab
2. Wait for "Bot running!" message
3. Check Telegram - send `/start` to your bot
4. Bot should respond!

## Step 6: Check Logs

```
Railway Dashboard → Logs → Watch your bot
```

Common issues:
- `Token error` → Check BOT_TOKEN variable
- `Database error` → Check DATABASE_URL format
- `Connection refused` → Bot still starting, wait 30 seconds

## Your Bot is LIVE!

Once deployed:
- ✅ Bot runs 24/7
- ✅ All features work
- ✅ Payments processed
- ✅ Database connected
- ✅ Admin dashboard works
- ✅ You're earning money!

## Railway Pricing

- **Free tier**: Included ($5/month credit)
- **Per additional usage**: Pay as you go
- **Your bot cost**: ~$2-5/month (very cheap!)

## Quick Reference

| What | Where |
|------|-------|
| Bot logs | Railway → Logs |
| Env vars | Railway → Variables |
| Restart bot | Railway → Redeploy |
| Connect GitHub | Railway → Source |
| View metrics | Railway → Metrics |

## If Something Goes Wrong

**Bot not starting:**
- Check logs in Railway
- Verify all env vars are set
- Make sure requirements.txt has all packages

**Database connection error:**
- Verify DATABASE_URL format
- Check Supabase project is running
- Try connection string from Supabase again

**Bot not responding:**
- Send `/start` command
- Check logs for errors
- Make sure BOT_TOKEN is correct

**Payments not working:**
- Verify Paystack keys
- Check payment webhooks are configured
- Test with small amount first

## Next Steps

After deployment:
1. Test all bot features in Telegram
2. Monitor logs for errors
3. Set up payment webhooks (optional)
4. Share bot with users
5. Start earning! 💰

## Support

- Railway Docs: https://docs.railway.app
- Python Telegram Bot: https://python-telegram-bot.readthedocs.io
- Supabase Docs: https://supabase.com/docs
- Paystack Docs: https://paystack.com/developers

---

**Your bot is production-ready!** Deploy now and start serving users! 🚀
