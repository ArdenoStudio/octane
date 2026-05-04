-- Migration 002: fx_rates table for live USD/LKR exchange rates
CREATE TABLE IF NOT EXISTS fx_rates (
  id          SERIAL PRIMARY KEY,
  recorded_at DATE NOT NULL,
  base        TEXT NOT NULL,
  target      TEXT NOT NULL,
  rate        NUMERIC(10,4) NOT NULL,
  UNIQUE (recorded_at, base, target)
);

CREATE INDEX IF NOT EXISTS idx_fx_rates_lookup
  ON fx_rates (base, target, recorded_at DESC);
