
-- =====================
-- Table: servo_stations
-- =====================
CREATE TABLE IF NOT EXISTS servo_stations (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    address       TEXT,
    brand_id      TEXT,
    contact_phone TEXT,
    latitude      NUMERIC(9, 6),
    longitude     NUMERIC(9, 6),
    opening_hours TEXT,
    mb_code21     TEXT,
    gcc_name21    TEXT,
    sa4_name21    TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_servo_stations_brand
ON servo_stations (brand_id);

CREATE INDEX IF NOT EXISTS idx_servo_stations_sa4
ON servo_stations (sa4_name21);

CREATE INDEX IF NOT EXISTS idx_servo_stations_gcc
ON servo_stations (gcc_name21);

CREATE INDEX IF NOT EXISTS idx_servo_stations_location
ON servo_stations USING gist (point(longitude, latitude));


-- =====================
-- Table: servo_prices
-- =====================
CREATE TABLE IF NOT EXISTS servo_prices (
    id           SERIAL PRIMARY KEY,
    station_id   TEXT NOT NULL REFERENCES servo_stations(id),
    fuel_type    TEXT NOT NULL,
    is_available BOOLEAN,
    price        NUMERIC,
    updated_at   TIMESTAMPTZ NOT NULL,
    recorded_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (station_id, fuel_type, updated_at)
);

CREATE INDEX IF NOT EXISTS idx_servo_prices_station_fuel
ON servo_prices (station_id, fuel_type, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_servo_prices_updated_at
ON servo_prices (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_servo_prices_fuel_type
ON servo_prices (fuel_type, updated_at DESC);


-- =====================
-- Table: market_data
-- =====================
CREATE TABLE IF NOT EXISTS market_data (
    id        SERIAL PRIMARY KEY,
    metric    TEXT NOT NULL,
    value     REAL NOT NULL,
    date      DATE NOT NULL,
    polled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (metric, date)
);

CREATE INDEX IF NOT EXISTS idx_market_data_metric_date
ON market_data (metric, date DESC);

CREATE INDEX IF NOT EXISTS idx_market_data_date
ON market_data (date DESC);