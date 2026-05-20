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

-- Push notification subscriptions for browser-based alerts
CREATE TABLE IF NOT EXISTS push_subscriptions (
  id          SERIAL PRIMARY KEY,
  alert_id    INTEGER REFERENCES alerts(id) ON DELETE CASCADE,
  endpoint    TEXT NOT NULL UNIQUE,
  p256dh_key  TEXT NOT NULL,
  auth_key    TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_alert
  ON push_subscriptions (alert_id);

-- Add push_enabled flag to alerts (one-time migration-safe approach)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'alerts' AND column_name = 'push_enabled'
  ) THEN
    ALTER TABLE alerts ADD COLUMN push_enabled BOOLEAN DEFAULT FALSE;
  END IF;
END $$;

-- Fuel stations for station locator
CREATE TABLE IF NOT EXISTS fuel_stations (
  id              SERIAL PRIMARY KEY,
  name            VARCHAR(255) NOT NULL,
  provider        VARCHAR(10) NOT NULL CHECK (provider IN ('CPC', 'LIOC')),
  address         TEXT,
  city            VARCHAR(100),
  district        VARCHAR(100),
  latitude        DECIMAL(10, 8),
  longitude       DECIMAL(11, 8),
  phone           VARCHAR(50),
  operating_hours VARCHAR(100),
  has_petrol_92   BOOLEAN DEFAULT TRUE,
  has_petrol_95   BOOLEAN DEFAULT TRUE,
  has_diesel      BOOLEAN DEFAULT TRUE,
  has_super_diesel BOOLEAN DEFAULT TRUE,
  last_verified_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stations_location
  ON fuel_stations (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_stations_provider
  ON fuel_stations (provider);
CREATE INDEX IF NOT EXISTS idx_stations_district
  ON fuel_stations (district);

-- Vehicle presets for multi-vehicle calculator
CREATE TABLE IF NOT EXISTS vehicle_presets (
  id              SERIAL PRIMARY KEY,
  category        VARCHAR(50) NOT NULL,
  name            VARCHAR(100) NOT NULL,
  fuel_type       VARCHAR(20) NOT NULL,
  avg_consumption DECIMAL(5, 2) NOT NULL,
  tank_capacity   DECIMAL(5, 2),
  popular         BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
