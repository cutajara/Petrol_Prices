CREATE TABLE market_data (
    id        SERIAL PRIMARY KEY,
    metric    TEXT NOT NULL,
    value     REAL NOT NULL,
    date      DATE NOT NULL,
    polled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (metric, date)
);

CREATE INDEX idx_market_data_metric_date
ON market_data (metric, date DESC);

CREATE INDEX idx_market_data_date
ON market_data (date DESC);

-- =====================
-- Table 1: Servo Stations
-- =====================
CREATE TABLE servo_stations (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    address       TEXT,
    brand_id      TEXT,
    contact_phone TEXT,
    latitude      NUMERIC(9, 6),
    longitude     NUMERIC(9, 6),
    opening_hours TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE servo_stations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public can read stations" ON servo_stations
    FOR SELECT USING (true);

-- Indexes
CREATE INDEX idx_servo_stations_brand
ON servo_stations (brand_id);

CREATE INDEX idx_servo_stations_location
ON servo_stations USING gist (point(longitude, latitude));


-- =====================
-- Table 2: Servo Prices
-- =====================
CREATE TABLE servo_prices (
    id           SERIAL PRIMARY KEY,
    station_id   TEXT NOT NULL REFERENCES servo_stations(id),
    fuel_type    TEXT NOT NULL,
    is_available BOOLEAN,
    price        NUMERIC(6, 2),
    updated_at   TIMESTAMPTZ NOT NULL,
    recorded_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (station_id, fuel_type, updated_at)
);

-- RLS
ALTER TABLE servo_prices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public can read prices" ON servo_prices
    FOR SELECT USING (true);

-- Indexes
CREATE INDEX idx_servo_prices_station_fuel
ON servo_prices (station_id, fuel_type, updated_at DESC);

CREATE INDEX idx_servo_prices_updated_at
ON servo_prices (updated_at DESC);

CREATE INDEX idx_servo_prices_fuel_type
ON servo_prices (fuel_type, updated_at DESC);