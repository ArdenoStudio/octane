-- Migration 006: email confirmation + fire history for alerts
ALTER TABLE alerts
  ADD COLUMN IF NOT EXISTS confirmed      BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS confirm_token  UUID    NOT NULL DEFAULT gen_random_uuid();

CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_confirm_token
  ON alerts (confirm_token);

-- All existing alerts are already live, so leave confirmed = TRUE.
-- New alerts inserted via subscribe() will explicitly set confirmed = FALSE.

CREATE TABLE IF NOT EXISTS alert_fires (
  id         SERIAL PRIMARY KEY,
  alert_id   INTEGER      NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
  fired_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  price_lkr  NUMERIC(8,2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alert_fires_alert_id
  ON alert_fires (alert_id, fired_at DESC);
