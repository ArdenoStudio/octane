-- Migration 007: track when Octane last verified source prices.
-- CPC revisions can be weeks apart; scraped_at / scrape_runs show check cadence.

ALTER TABLE fuel_prices
  ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_fuel_prices_scraped_at
  ON fuel_prices (source, scraped_at DESC);

CREATE TABLE IF NOT EXISTS scrape_runs (
  id            SERIAL PRIMARY KEY,
  source        TEXT NOT NULL,
  checked_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  rows_upserted INTEGER NOT NULL DEFAULT 0,
  ok            BOOLEAN NOT NULL DEFAULT TRUE,
  detail        TEXT
);

CREATE INDEX IF NOT EXISTS idx_scrape_runs_source_checked
  ON scrape_runs (source, checked_at DESC);
