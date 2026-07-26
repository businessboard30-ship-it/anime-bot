# Setup Supabase Database

## Step 1: Get Your Supabase Credentials

Your Supabase integration is already connected! Get your credentials:

1. Go to your Supabase project dashboard
2. Click "Settings" (bottom left)
3. Click "Database"
4. Copy the connection string (PostgreSQL format)
5. Extract these values:
   - `NEXT_PUBLIC_SUPABASE_URL` - Your project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Your anon public key

## Step 2: Create the Database Schema

### Option A: Run SQL in Supabase Console (Recommended)

1. In Supabase: Go to SQL Editor
2. Click "New Query"
3. Copy the entire content from `sql/schema.sql`
4. Paste it into the SQL editor
5. Click "Run"
6. Wait 10-20 seconds for completion
7. You should see "MIGRATION COMPLETE" message

### Option B: Use the Supabase Dashboard

1. Supabase → SQL Editor
2. New Query
3. Paste the SQL code
4. Run

## Step 3: Verify Tables Created

After running the SQL:

1. Supabase → Table Editor (left sidebar)
2. You should see these 10 tables:
   - users
   - anime_entries
   - submissions
   - cloned_bots
   - payment_logs
   - commission_tracking
   - subscription_payments
   - ai_usage_tracking
   - bot_analytics
   - admin_logs

## Step 4: Update Environment Variables

1. Copy `.env.local.example` to `.env.local`
2. Replace placeholder values:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_project_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
   ```
3. Keep other values as they are (already filled in)

## Step 5: Test Connection

Your bot code will automatically connect to Supabase when it needs data.

## Getting Your Credentials

### Supabase URL and Keys

1. Supabase Dashboard
2. Settings (bottom left)
3. API tab
4. You'll see:
   - Project URL
   - anon/public key
   - service_role key (don't use for client)

## Database Schema

The schema includes:

**Tables (10):**
- `users` - User profiles and subscription info
- `anime_entries` - Anime database
- `submissions` - User-submitted anime
- `cloned_bots` - Bot clone instances
- `payment_logs` - Payment transactions
- `commission_tracking` - Bot clone commissions
- `subscription_payments` - Monthly subscriptions
- `ai_usage_tracking` - AI feature analytics
- `bot_analytics` - Bot performance metrics
- `admin_logs` - Admin action history

**Indexes (20+):** For fast queries on user lookups, payments, statuses, etc.

**Views (3):** 
- `active_subscribers` - Current active subscriptions
- `monthly_revenue` - Revenue reports by month
- `top_cloned_bots_revenue` - Top performing clones

## Troubleshooting

### Error: "Table already exists"
- This is fine! Just means tables were already created
- You can run the SQL again, it will skip existing tables

### Error: "column does not exist"
- Make sure you're using the corrected SQL from `sql/schema.sql`
- This has the proper column names (e.g., `created_date` instead of `created_at`)

### Connection refused
- Check that Supabase project is running
- Verify URL and keys in `.env.local`
- Check that firewall allows Supabase IPs

## Next Steps

1. ✅ Database created
2. ✅ Tables initialized
3. Next: Deploy bot to Vercel
4. Next: Configure webhook
5. Next: Start earning!

Your database is now ready!
