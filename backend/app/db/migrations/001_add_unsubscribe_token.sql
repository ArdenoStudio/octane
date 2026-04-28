-- Migration 001: add unsubscribe_token to existing alerts table
-- Run once on any database created before this change.
-- Safe to run multiple times (uses IF NOT EXISTS / DO NOTHING patterns).

ALTER TABLE alerts
  ADD COLUMN IF NOT EXISTS unsubscribe_token UUID DEFAULT gen_random_uuid();

-- Backfill any rows that got NULL (shouldn't happen with DEFAULT, but belt-and-suspenders)
UPDATE alerts SET unsubscribe_token = gen_random_uuid() WHERE unsubscribe_token IS NULL;

-- Now enforce NOT NULL
ALTER TABLE alerts ALTER COLUMN unsubscribe_token SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_unsubscribe_token
  ON alerts (unsubscribe_token);
