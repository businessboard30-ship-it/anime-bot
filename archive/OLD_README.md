# Anime Discovery Bot

A feature-rich Telegram bot for discovering, sharing, and managing anime and movies with bot cloning capabilities.

## Features

### 🎬 Core Features
- **Trending Anime**: Browse the most popular anime right now
- **Latest Releases**: Discover new anime episodes and series
- **Ongoing Series**: Keep track of currently airing anime
- **Seasonal Anime**: Explore this season's anime
- **Movie Discovery**: Find anime movies
- **Search**: Search for specific anime by title
- **Categories**: Organize anime by genres and preferences

### 📤 User Contributions
- Submit your favorite anime for review
- Admin review and approval system
- Organized submission queue
- User notifications on approval/rejection

### 🤖 Bot Cloning (50 GHS)
- Create your own independent bot instance
- Full customization:
  - Custom bot name
  - Webhook URL for submissions
  - Branding and description
  - Service categories
- Paystack payment integration
- All features inherited from main bot

### 💫 Beautiful UI
- Organized inline keyboard with grouped buttons (2-3 per row)
- Unique emoji color for each action type
- Smooth animations and loading states
- Minimal text, maximum clarity
- Pagination for browsing lists

## Tech Stack

- **Framework**: python-telegram-bot (v20+)
- **APIs**: AniList GraphQL + Jikan REST
- **Database**: SQLite (local) / PostgreSQL (production)
- **Payment**: Paystack
- **Deployment**: Railway.app (or Vercel)

## Project Structure

```
anime_bot/
├── main.py                 # Bot entry point
├── config.py              # Configuration & constants
├── database.py            # Database models & operations
├── anime_service.py       # AniList & Jikan API integration
├── keyboards.py           # UI button layouts
├── formatter.py           # Text formatting utilities
├── payments.py            # Paystack integration
├── requirements.txt       # Python dependencies
├── Procfile               # Railway deployment config
├── .env.example           # Environment variables template
├── handlers/
│   ├── discover.py        # Trending/latest/ongoing browsing
│   ├── search.py          # Search functionality
│   ├── submit.py          # User submissions
│   ├── admin_panel.py     # Admin review interface
│   └── clone_bot.py       # Bot cloning & customization
└── README.md
```

## Setup Instructions

### 1. Local Development

**Prerequisites:**
- Python 3.9+
- pip or poetry

**Installation:**

```bash
# Clone the repository
git clone <repo-url>
cd anime_bot

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env

# Configure .env with your values
SINOBANED2_BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_telegram_user_id
```

**Get a Telegram Bot Token:**
1. Open Telegram and search for `@BotFather`
2. Start the bot and use `/newbot`
3. Follow the instructions to create your bot
4. Copy the token to your `.env`

**Get Your Admin ID:**
1. Start your bot and message it: `/start`
2. Check bot logs or use `@userinfobot` to get your user ID
3. Add to `ADMIN_ID` in `.env`

**Run Locally:**

```bash
python main.py
```

### 2. Paystack Configuration

**Get Paystack Credentials:**
1. Create account at https://paystack.com
2. Go to Settings → API Keys & Webhooks
3. Copy Secret and Public keys to `.env`

**Set Webhook (for production):**
1. In Paystack dashboard, set webhook URL
2. Webhook will notify bot of payment completion

### 3. Railway.app Deployment

**Setup PostgreSQL Database:**
1. Create new Railway project
2. Add PostgreSQL plugin
3. Copy connection string to `DATABASE_URL`

**Deploy Bot:**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Set environment variables
railway variables

# Add each env var from .env.example

# Deploy
railway up
```

**Enable Long-Running Worker:**
1. In Railway dashboard, go to Settings
2. Set Deployment Trigger to "Manual" or continuous
3. Configure worker restart policy

### 4. Alternative: Vercel Deployment

For Vercel serverless functions (requires webhooks):

```bash
# Deploy with Vercel
vercel deploy

# Set environment variables in Vercel dashboard
```

## Usage

### User Commands

- `/start` - Start the bot and show main menu
- Click buttons to browse anime, search, submit, or clone
- Admin-only: `/admin` - Access admin dashboard

### Admin Panel

- Review pending submissions
- Approve/reject user submissions
- View bot statistics
- Manage cloned bot instances

### Main Menu Buttons

```
🔥 Trending    ✨ Latest
🔄 Ongoing     📅 Season
🎬 Movies      🔍 Search
📚 Categories  📤 Submit
🤖 Clone Bot
```

## API Integration

### AniList GraphQL
- Comprehensive anime database
- Trending, seasonal, and search queries
- Episode information

### Jikan API
- MyAnimeList data
- Alternative source for anime details
- Episode listings

## Database Schema

### Users
- user_id, username, first_name, joined_date, submissions_count, is_admin

### Submissions
- submission_id, user_id, anime_name, episodes, genres, synopsis, status

### Cloned Bots
- clone_id, owner_id, bot_name, bot_token, webhook_url, custom_data, status

### Anime Entries
- anime_id, title, episodes, genres, rating, status, synopsis, image_url

## Customization

### Change Colors/Emojis
Edit `config.py` `EMOJI_COLORS` dictionary:

```python
EMOJI_COLORS = {
    "trending": "🔥",
    "latest": "✨",
    # ... customize as needed
}
```

### Modify Button Layouts
Edit `keyboards.py` to reorganize or add new button groups

### Adjust Pagination
Change `PAGINATION_SIZE` in `config.py`

## Troubleshooting

### Bot not responding
- Check bot token in `.env`
- Verify bot is running: `python main.py`
- Check console for errors

### Database errors
- Ensure DATABASE_URL is correct
- For SQLite: check file permissions
- For PostgreSQL: verify connection string

### Payment not working
- Verify Paystack keys are correct
- Check webhook URL is set in Paystack dashboard
- Test in sandbox mode first

### API rate limits
- AniList and Jikan have rate limits
- Bot implements caching to reduce API calls
- Cache TTL is 1 hour by default

## Environment Variables

```
SINOBANED2_BOT_TOKEN      # Telegram bot token
ADMIN_ID                  # Your Telegram user ID
DATABASE_URL              # SQLite path or PostgreSQL connection string
PAYSTACK_SECRET_KEY       # Paystack API secret key
PAYSTACK_PUBLIC_KEY       # Paystack API public key
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Verify all environment variables are set
4. Check API status (AniList, Jikan, Paystack)

## License

This project is provided as-is for personal use.

## Credits

- **Telegram Bot API**: python-telegram-bot library
- **Anime Data**: AniList (GraphQL) and Jikan (MyAnimeList wrapper)
- **Payments**: Paystack
- **Hosting**: Railway.app

---

**Version**: 1.0.0  
**Last Updated**: 2026-07-26
