-- Octane DB schema. Idempotent — safe to re-run.

CREATE TABLE IF NOT EXISTS fuel_prices (
  id          SERIAL PRIMARY KEY,
  recorded_at DATE NOT NULL,
  fuel_type   TEXT NOT NULL,
  price_lkr   NUMERIC(8,2) NOT NULL,
  source      TEXT NOT NULL,
  UNIQUE (recorded_at, fuel_type, source)
);

CREATE INDEX IF NOT EXISTS idx_fuel_prices_lookup
  ON fuel_prices (fuel_type, source, recorded_at DESC);

CREATE TABLE IF NOT EXISTS world_prices (
  id          SERIAL PRIMARY KEY,
  recorded_at DATE NOT NULL,
  country     TEXT NOT NULL,
  fuel_type   TEXT NOT NULL,
  price_usd   NUMERIC(6,3) NOT NULL,
  UNIQUE (recorded_at, country, fuel_type)
);

CREATE INDEX IF NOT EXISTS idx_world_prices_lookup
  ON world_prices (fuel_type, recorded_at DESC);

CREATE TABLE IF NOT EXISTS alerts (
  id                SERIAL PRIMARY KEY,
  email             TEXT NOT NULL,
  fuel_type         TEXT NOT NULL,
  threshold         NUMERIC(8,2) NOT NULL,
  direction         TEXT NOT NULL CHECK (direction IN ('above','below')),
  active            BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_fired_at     TIMESTAMPTZ,
  unsubscribe_token UUID NOT NULL DEFAULT gen_random_uuid()
);

CREATE INDEX IF NOT EXISTS idx_alerts_active
  ON alerts (active, fuel_type);

CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_unsubscribe_token
  ON alerts (unsubscribe_token);
