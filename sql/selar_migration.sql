-- Selar/Zapier fulfillment ledger. Apply once before enabling the webhook.
CREATE TABLE IF NOT EXISTS selar_sales (
  sale_id TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  entitlement TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_selar_sales_user_id ON selar_sales(user_id);

CREATE TABLE IF NOT EXISTS manual_payment_reviews (
  reference TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  payment_type TEXT NOT NULL,
  clone_id BIGINT NOT NULL DEFAULT 0,
  context JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL CHECK (status IN ('awaiting_review', 'approved', 'rejected')),
  decided_by BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  decided_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_manual_payment_reviews_status ON manual_payment_reviews(status);

-- Manual clone-payment review. The buyer taps a button in Telegram and the
-- admin approves or rejects from a private DM; no cron or payment API lookup.
ALTER TABLE clone_payments
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_clone_payments_status ON clone_payments(status);
