# Deployment Guide - Railway.app

Complete step-by-step guide to deploy the Anime Bot to Railway.app

## Prerequisites

- GitHub account with repository pushed
- Railway.app account (free tier available)
- Telegram Bot Token (from BotFather)
- Paystack API keys
- Your Telegram admin ID

## Step 1: Create Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Connect your GitHub account
5. Select your anime-bot repository
6. Railway will auto-detect it's a Python project

## Step 2: Add PostgreSQL Database

1. In Railway dashboard, click "Add Service"
2. Select "PostgreSQL"
3. A PostgreSQL instance will be created
4. Copy the `DATABASE_URL` connection string

## Step 3: Configure Environment Variables

In Railway dashboard, go to "Variables":

```
SINOBANED2_BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_telegram_user_id
DATABASE_URL=postgresql://user:pass@host:port/db
PAYSTACK_SECRET_KEY=your_paystack_secret_key
PAYSTACK_PUBLIC_KEY=your_paystack_public_key
```

### How to get each variable:

**SINOBANED2_BOT_TOKEN:**
1. Open Telegram, search for @BotFather
2. Use `/newbot` to create a bot
3. Copy the token provided

**ADMIN_ID:**
1. Send a message to your bot
2. Use `/start` command
3. Check the message sender's ID (or use @userinfobot)

**DATABASE_URL:**
1. In Railway, click PostgreSQL service
2. Go to "Connect"
3. Copy "Postgres Connection String"

**PAYSTACK_SECRET_KEY & PAYSTACK_PUBLIC_KEY:**
1. Create account at https://paystack.com
2. Go to Settings → API Keys & Webhooks
3. Copy both Secret and Public keys

## Step 4: Deploy

1. Railway automatically deploys from your repository
2. Go to "Deployments" tab
3. You'll see deployment progress
4. Once green checkmark appears, your bot is running!

## Step 5: Verify Deployment

1. Go to Railway logs
2. You should see: `[v0] Starting Anime Bot...`
3. Then: `[v0] Bot is polling...`
4. If errors appear, check environment variables

## Step 6: Test Your Bot

1. Open Telegram
2. Search for your bot by name
3. Send `/start` command
4. You should see the main menu

## Step 7: Configure Webhook for Payments (Optional)

For production Paystack integration:

1. Get your Railway bot URL: `https://your-railway-app.up.railway.app`
2. In Paystack dashboard, go to Settings → API Keys & Webhooks
3. Set Webhook URL to: `https://your-railway-app.up.railway.app/webhook/paystack`
4. Select events: `charge.success`, `charge.failed`

## Troubleshooting

### Bot not responding
**Problem**: Bot doesn't reply to `/start`
**Solution**:
1. Check Railway logs for errors
2. Verify `SINOBANED2_BOT_TOKEN` is correct
3. Make sure bot is still deployed (check green status)
4. Restart the deployment

### Database connection error
**Problem**: "Can't connect to database"
**Solution**:
1. Verify `DATABASE_URL` is correct
2. Check PostgreSQL service is running
3. Ensure PostgreSQL service is linked to bot deployment
4. Restart both services

### Payment errors
**Problem**: "Payment failed" or webhook not working
**Solution**:
1. Verify Paystack keys in environment variables
2. Test in Paystack sandbox mode first
3. Check webhook URL configuration
4. Review Paystack logs for more details

### Out of memory
**Problem**: Bot crashes with memory error
**Solution**:
1. Upgrade Railway plan to get more resources
2. Clear bot cache (will happen automatically)
3. Reduce pagination size if needed

## Monitoring

### Check Logs
```
Railway Dashboard → Logs tab
- Shows real-time bot activity
- Errors appear in red
- Useful for debugging
```

### Check Metrics
```
Railway Dashboard → Metrics tab
- CPU usage
- Memory usage
- Network activity
- Disk space
```

### Auto-restart
Railway automatically restarts your bot if it crashes. You can configure restart policies in Settings.

## Updating Your Bot

When you make code changes:

1. Push to GitHub: `git push origin main`
2. Railway detects the push automatically
3. New deployment starts automatically
4. Old deployment shuts down, new one starts
5. Your bot uses the updated code

## Production Checklist

- [ ] Bot token set correctly
- [ ] Admin ID configured
- [ ] PostgreSQL database created
- [ ] DATABASE_URL set
- [ ] Paystack keys added
- [ ] Bot responding to /start
- [ ] Database tables created (first run)
- [ ] Can browse anime categories
- [ ] Search functionality works
- [ ] Submissions system works
- [ ] Payment integration works (if enabled)

## Cost Estimation

**Railway.app Free Tier:**
- $5 free credits per month
- Enough for small bot (<100 users)
- PostgreSQL database included

**If you exceed free tier:**
- Pay-as-you-go pricing
- Typical bot usage: $5-20/month
- Upgrade anytime, no long-term contracts

## Next Steps

1. **Configure Admin**: Set up admin features
2. **Test Features**: Try each feature thoroughly
3. **Monitor Logs**: Watch for errors initially
4. **Scale Up**: Upgrade plan if needed
5. **Backup Data**: Set up database backups

## Support

- Railway Docs: https://docs.railway.app
- Python Telegram Bot: https://python-telegram-bot.readthedocs.io
- AniList API: https://anilist.gitbook.io/anilist-apiv2-docs
- Paystack Docs: https://paystack.com/developers

## Emergency Procedures

### Bot crashed and won't restart
1. Go to Railway dashboard
2. Click the bot service
3. Click "Restart" button
4. Check logs for error messages
5. Fix environment variables if needed

### Database corrupted
1. Create new PostgreSQL service in Railway
2. Update DATABASE_URL with new connection string
3. Restart bot (it will recreate tables)
4. Old data will be lost (consider backup first)

### Need to rollback deployment
1. Go to Deployments tab
2. Select previous deployment
3. Click "Rollback" button
4. Bot will revert to previous version

---

**Last Updated**: 2026-07-26  
**Bot Version**: 1.0.0
