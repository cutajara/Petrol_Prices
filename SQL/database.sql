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