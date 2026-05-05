-- Migration 005: weekly digest subscriber list
CREATE TABLE IF NOT EXISTS digest_subscribers (
  id                SERIAL PRIMARY KEY,
  email             TEXT NOT NULL UNIQUE,
  active            BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_sent_at      TIMESTAMPTZ,
  unsubscribe_token UUID NOT NULL DEFAULT gen_random_uuid()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_digest_unsubscribe_token
  ON digest_subscribers (unsubscribe_token);
