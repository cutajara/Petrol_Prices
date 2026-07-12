import os
import logging
import psycopg2
import psycopg2.extras
import pandas as pd
from supabase import create_client
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- Supabase connection ---
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

RDS_ENDPOINT = os.environ["RDS_ENDPOINT"]
RDS_SECRET = os.environ["RDS_SECRET"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- RDS connection ---
rds = psycopg2.connect(
    host=f"{RDS_ENDPOINT}.ap-southeast-2.rds.amazonaws.com",
    port=5432,
    dbname="petrol_predictor",
    user="petrol_admin",
    password=RDS_SECRET,
    connect_timeout=10,
    sslmode="require",
)
rds.autocommit = False
cur = rds.cursor()

BATCH_SIZE = 1000  # rows per insert batch


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def fetch_all_supabase(table: str, columns: str = "*") -> pd.DataFrame:
    all_rows  = []
    page_size = 1000
    start     = 0

    while True:
        result = (
            supabase.table(table)
            .select(columns)
            .range(start, start + page_size - 1)
            .execute()
        )
        rows = result.data
        if not rows:
            break
        all_rows.extend(rows)
        logger.info(f"  {table}: fetched {len(all_rows):,} rows so far...")
        if len(rows) < page_size:
            break
        start += page_size  # ← this was the bug

    return pd.DataFrame(all_rows)


def batch_insert(table: str, columns: list, rows: list, on_conflict: str = "") -> int:
    """Insert rows in batches using executemany."""
    if not rows:
        return 0

    placeholders = ",".join(["%s"] * len(columns))
    col_names    = ",".join(columns)
    sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) {on_conflict}"

    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        cur.executemany(sql, batch)
        rds.commit()
        inserted += len(batch)
        logger.info(f"  {table}: {inserted:,} / {len(rows):,} rows inserted")

    return inserted


def verify_counts(table: str, expected: int):
    """Verify row count in RDS matches expected."""
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    actual = cur.fetchone()[0]
    status = "✅" if actual == expected else "❌"
    logger.info(f"{status} {table}: expected {expected:,}, got {actual:,}")
    return actual == expected


# ---------------------------------------------------------------
# Step 1 — Migrate servo_stations
# ---------------------------------------------------------------

def migrate_stations():
    logger.info("=" * 50)
    logger.info("MIGRATING servo_stations")
    logger.info("=" * 50)

    df = fetch_all_supabase("servo_stations")

    columns = [
        "id", "name", "address", "brand_id", "contact_phone",
        "latitude", "longitude", "opening_hours",
        "mb_code21", "gcc_name21", "sa4_name21",
        "created_at", "updated_at"
    ]

    # Fill missing columns with None
    for col in columns:
        if col not in df.columns:
            df[col] = None

    rows = [tuple(row) for row in df[columns].values]

    # Upsert — safe to rerun
    on_conflict = "ON CONFLICT (id) DO UPDATE SET updated_at = EXCLUDED.updated_at"
    inserted = batch_insert("servo_stations", columns, rows, on_conflict)
    verify_counts("servo_stations", len(df))
    return len(df)


# ---------------------------------------------------------------
# Step 2 — Migrate servo_prices
# ---------------------------------------------------------------

def migrate_prices():
    logger.info("=" * 50)
    logger.info("MIGRATING servo_prices")
    logger.info("=" * 50)

    df = fetch_all_supabase(
        "servo_prices",
        "station_id, fuel_type, is_available, price, updated_at, recorded_at"
    )

    columns = [
        "station_id", "fuel_type", "is_available",
        "price", "updated_at", "recorded_at"
    ]

    # Convert NaN prices to None
    df['price'] = df['price'].where(df['price'].notna(), None)

    rows = [tuple(row) for row in df[columns].values]

    # Skip duplicates — unique constraint handles it
    on_conflict = "ON CONFLICT (station_id, fuel_type, updated_at) DO NOTHING"
    inserted = batch_insert("servo_prices", columns, rows, on_conflict)
    verify_counts("servo_prices", len(df))
    return len(df)


# ---------------------------------------------------------------
# Step 3 — Migrate market_data
# ---------------------------------------------------------------

def migrate_market_data():
    logger.info("=" * 50)
    logger.info("MIGRATING market_data")
    logger.info("=" * 50)

    df = fetch_all_supabase("market_data", "metric, value, date, polled_at")

    columns = ["metric", "value", "date", "polled_at"]
    rows    = [tuple(row) for row in df[columns].values]

    # Skip duplicates
    on_conflict = "ON CONFLICT (metric, date) DO NOTHING"
    inserted = batch_insert("market_data", columns, rows, on_conflict)
    verify_counts("market_data", len(df))
    return len(df)


# ---------------------------------------------------------------
# Step 4 — Top-up migration
# Captures any rows that arrived in Supabase during migration
# ---------------------------------------------------------------

def topup_prices(cutoff: str):
    logger.info("=" * 50)
    logger.info("TOP-UP — servo_prices since cutoff")
    logger.info("=" * 50)

    result = (
        supabase.table("servo_prices")
        .select("station_id, fuel_type, is_available, price, updated_at, recorded_at")
        .gt("recorded_at", cutoff)
        .execute()
    )
    df = pd.DataFrame(result.data)

    if df.empty:
        logger.info("No new rows since cutoff — nothing to top up")
        return 0

    logger.info(f"Top-up rows: {len(df):,}")
    df['price'] = df['price'].where(df['price'].notna(), None)

    columns = ["station_id", "fuel_type", "is_available",
               "price", "updated_at", "recorded_at"]
    rows = [tuple(row) for row in df[columns].values]

    on_conflict = "ON CONFLICT (station_id, fuel_type, updated_at) DO NOTHING"
    batch_insert("servo_prices", columns, rows, on_conflict)
    return len(df)


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def run():
    # Cutoff — rows after this timestamp get captured in top-up
    CUTOFF = "2026-07-11 21:02:34.156157+00"

    start = datetime.now(timezone.utc)
    logger.info(f"Migration started at {start.isoformat()}")

    # Migrate all three tables
    stations_count = migrate_stations()
    prices_count   = migrate_prices()
    market_count   = migrate_market_data()

    # Top-up — catch anything new since cutoff
    topup_count = topup_prices(CUTOFF)

    # Final summary
    end = datetime.now(timezone.utc)
    duration = (end - start).seconds

    logger.info("=" * 50)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 50)
    logger.info(f"servo_stations:  {stations_count:,} rows")
    logger.info(f"servo_prices:    {prices_count:,} rows + {topup_count:,} top-up")
    logger.info(f"market_data:     {market_count:,} rows")
    logger.info(f"Duration:        {duration}s")
    logger.info("=" * 50)

    cur.close()
    rds.close()


if __name__ == "__main__":
    run()
