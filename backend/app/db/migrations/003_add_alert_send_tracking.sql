-- Migration 003: track failed alert send attempts for reliability / retry logic
ALTER TABLE alerts
  ADD COLUMN IF NOT EXISTS send_attempts   INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_send_error TEXT;
