# Deploy Your Anime Bot to Vercel (FREE FOREVER!)

Vercel allows you to host your Telegram bot **completely free forever** using serverless functions. This guide shows you how.

## Why Vercel?

✓ **Completely FREE** - No costs, ever (generous free tier)
✓ **Instant Scaling** - Handles millions of requests
✓ **High Uptime** - 99.99% availability
✓ **CDN Included** - Fast globally
✓ **Easy Deploy** - Git push = instant deploy
✓ **No Server Management** - We handle it all

## Prerequisites

1. Telegram bot token (from @BotFather)
2. Vercel account (free at vercel.com)
3. GitHub account (free at github.com)
4. Groq API key (free at console.groq.com)
5. PostgreSQL database (we recommend Supabase - free tier available)

## Step 1: Prepare Your Bot for Vercel

Your bot uses **webhooks** instead of polling. The `api/bot.py` file is already configured as a Vercel serverless function.

### Key Files for Vercel:

```
/api/bot.py          <- Webhook handler (Vercel calls this)
/vercel.json         <- Vercel configuration
```

### Create vercel.json

```json
{
  "buildCommand": "pip install -r requirements.txt",
  "functions": {
    "api/bot.py": {
      "memory": 512,
      "maxDuration": 60
    }
  },
  "env": [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_BOT_USERNAME",
    "ADMIN_ID",
    "GROQ_API_KEY",
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "DATABASE_URL",
    "USE_POSTGRESQL"
  ]
}
```

## Step 2: Set Up PostgreSQL Database

**Option A: Supabase (Recommended)**

1. Go to supabase.com
2. Create a free account
3. Create new project
4. Get your PostgreSQL connection string
5. Copy it to `DATABASE_URL`

**Option B: Railway.app**

1. Go to railway.app
2. Create account
3. Add PostgreSQL database
4. Get connection string

**Option C: AWS RDS Free Tier**

1. Create AWS account
2. Set up RDS PostgreSQL
3. Get connection details

## Step 3: Push Code to GitHub

```bash
# Initialize git
git init

# Add files
git add .

# Commit
git commit -m "Initial anime bot commit"

# Add remote (replace with your GitHub URL)
git remote add origin https://github.com/YOUR_USERNAME/anime-bot.git

# Push to GitHub
git push -u origin main
```

## Step 4: Deploy to Vercel

### Method 1: Vercel Dashboard (Easiest)

1. Go to vercel.com
2. Click "Import Project"
3. Select "Import Git Repository"
4. Paste your GitHub repo URL
5. Click Import

### Method 2: Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Follow prompts
```

## Step 5: Configure Environment Variables

1. Go to Vercel Dashboard
2. Select your project
3. Go to Settings → Environment Variables
4. Add these variables:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username_here
ADMIN_ID=your_telegram_user_id
GROQ_API_KEY=your_groq_key_here
PAYSTACK_SECRET_KEY=your_paystack_secret
PAYSTACK_PUBLIC_KEY=your_paystack_public
DATABASE_URL=postgresql://user:password@host/database
USE_POSTGRESQL=true
```

## Step 6: Set Telegram Webhook

Your bot URL will be: `https://your-project-name.vercel.app/api/bot`

Run this command with your bot token:

```bash
curl -X POST https://api.telegram.org/bot{YOUR_BOT_TOKEN}/setWebhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-project-name.vercel.app/api/bot"}'
```

Or run from Python:

```python
import requests

token = "YOUR_BOT_TOKEN"
url = "https://your-project-name.vercel.app/api/bot"

response = requests.post(
    f"https://api.telegram.org/bot{token}/setWebhook",
    json={"url": url}
)

print(response.json())
```

## Step 7: Test Your Bot

1. Find your bot on Telegram
2. Send `/start`
3. Click buttons and test features
4. Check Vercel logs for any errors

**View Logs:**
- Go to Vercel Dashboard
- Click your project
- Go to "Deployments" tab
- Click latest deployment
- Click "Logs"

## Configuration Files Needed

### requirements.txt
Already included, but make sure it has:
- python-telegram-bot
- aiohttp
- aiosqlite / psycopg2
- requests

### .env (Don't push to GitHub!)

```
TELEGRAM_BOT_TOKEN=token_here
TELEGRAM_BOT_USERNAME=bot_name
ADMIN_ID=your_id
GROQ_API_KEY=groq_key
DATABASE_URL=postgres://...
USE_POSTGRESQL=true
```

## Monitoring & Logs

### View Real-Time Logs

```bash
vercel logs --tail
```

### Check Bot Health

```bash
curl https://api.telegram.org/bot{TOKEN}/getMe
```

Should return JSON with bot info.

### Monitor Errors

1. Vercel Dashboard → Deployments
2. Click the deployment
3. Scroll to "Logs" section
4. See real-time output

## Cost Breakdown (Completely Free!)

- **Vercel Functions**: FREE
- **Bandwidth**: 100 GB/month FREE
- **Database** (Supabase): 500 MB FREE
- **Groq API**: Free tier sufficient
- **Telegram Bot**: Always FREE

**Total Cost: $0**

## Common Issues & Fixes

### Bot Not Responding

**Issue**: Bot doesn't reply to messages

**Fix**:
1. Check webhook is set correctly:
   ```bash
   curl https://api.telegram.org/bot{TOKEN}/getWebhookInfo
   ```

2. Verify environment variables in Vercel are set

3. Check logs for errors

### "ModuleNotFoundError"

**Issue**: Missing Python package

**Fix**:
1. Add to `requirements.txt`
2. Commit and push
3. Vercel redeploys automatically

### Database Connection Failed

**Issue**: Can't connect to PostgreSQL

**Fix**:
1. Verify DATABASE_URL format
2. Check database credentials
3. Whitelist Vercel IP (varies, usually all IPs for security)
4. Test connection locally first

### Webhook URL Invalid

**Issue**: Telegram says URL is invalid

**Fix**:
1. Make sure URL is HTTPS (Vercel provides this)
2. Check domain is correct
3. Bot needs to be public
4. Try simple test request:
   ```bash
   curl https://your-url.vercel.app/api/bot
   ```

## Performance Tips

### Optimize Cold Starts
- Keep code modular
- Lazy load libraries
- Use caching where possible

### Monitor Function Duration
- Set maxDuration in vercel.json
- Telegram needs response within 30 seconds
- Keep function execution < 5 seconds for best performance

### Scale Subscriptions
- Vercel auto-scales
- Handle 1000+ concurrent users easily
- No configuration needed

## Migrating from Railway to Vercel

If you're switching from Railway:

1. Export your PostgreSQL database
2. Import to new database (Supabase/RDS)
3. Update DATABASE_URL in Vercel
4. Push to GitHub
5. Vercel auto-deploys

**Zero downtime migration!**

## Advanced: Custom Domain

1. Go to Vercel project settings
2. Click "Domains"
3. Add your domain
4. Update DNS records
5. Your bot now runs on your domain!

## Maintenance

### Weekly
- Monitor logs
- Check error rates
- Review analytics

### Monthly
- Update dependencies
- Check for security updates
- Review database usage

### Quarterly
- Full backup of database
- Review bot analytics
- Plan new features

## Need Help?

### Common Resources
- Telegram Bot API: core.telegram.org/bots
- Vercel Docs: vercel.com/docs
- Groq API: console.groq.com
- PostgreSQL: postgresql.org/docs

### Debugging Tips

1. Enable verbose logging
2. Check Vercel Function logs
3. Test locally first
4. Use Telegram Bot API tester

## Next Steps

1. Deploy this guide and test
2. Monitor for 24 hours
3. Gather feedback
4. Iterate and improve
5. Scale to more users

Your bot is now **production-ready on Vercel!** 🚀

---

## Quick Checklist

- [ ] GitHub repo created
- [ ] Code pushed to GitHub
- [ ] Vercel project created
- [ ] Environment variables set
- [ ] Database configured
- [ ] Webhook URL set
- [ ] Bot tested in Telegram
- [ ] Logs monitored
- [ ] Errors fixed
- [ ] Bot responding to messages
- [ ] Features working correctly
- [ ] Ready for public!

**Congratulations! Your bot is live on Vercel! 🎉**
