import uuid
import logging
import os
import json
import boto3
import psycopg2
import psycopg2.extras
import requests
import pandas as pd
from datetime import datetime, timezone
import sys
from pathlib import Path
MARKET_DIR = Path(__file__).resolve().parent
if str(MARKET_DIR) not in sys.path:
    sys.path.insert(0, str(MARKET_DIR))

from get_servo_saver import fetch_api, process_response

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- Config ---
SECRET_NAME = os.environ.get("SECRET_NAME", "petrol-predictor/rds")
RDS_ENDPOINT = os.environ.get("RDS_ENDPOINT", "petrol-predictor/rds")
API_URL     = "https://api.fuel.service.vic.gov.au/open-data/v1/fuel/prices"


# ---------------------------------------------------------------
# Database
# ---------------------------------------------------------------

def get_db_credentials() -> dict:
    """Fetch RDS credentials from Secrets Manager."""
    client = boto3.client("secretsmanager", region_name="ap-southeast-2")
    secret = client.get_secret_value(SecretId=SECRET_NAME)
    return json.loads(secret["SecretString"])


def get_db_connection():
    """Get a psycopg2 connection using Secrets Manager credentials."""
    creds = get_db_credentials()
    return psycopg2.connect(
        host=f"{RDS_ENDPOINT}.ap-southeast-2.rds.amazonaws.com",
        port=5432,
        dbname="petrol_predictor",
        user=creds["username"],
        password=creds["password"],
        sslmode="require",
        connect_timeout=10,
    )


# ---------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------

def upsert_stations(conn, stations_df: pd.DataFrame) -> None:
    """Upsert station records into RDS."""
    columns = [
        "id", "name", "address", "brand_id", "contact_phone",
        "latitude", "longitude", "opening_hours",
    ]

    now = datetime.now(timezone.utc)

    rows = []
    for _, row in stations_df.iterrows():
        row_tuple = []
        for col in columns:
            val = row.get(col)
            # Check if the value is a dictionary and serialize it to a JSON string
            if isinstance(val, dict):
                val = json.dumps(val)
            row_tuple.append(val)
            
        # Append the parsed columns plus the 'now' timestamp
        rows.append(tuple(row_tuple) + (now,))

    sql = """
        INSERT INTO servo_stations
            (id, name, address, brand_id, contact_phone,
             latitude, longitude, opening_hours, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name          = EXCLUDED.name,
            address       = EXCLUDED.address,
            brand_id      = EXCLUDED.brand_id,
            contact_phone = EXCLUDED.contact_phone,
            latitude      = EXCLUDED.latitude,
            longitude     = EXCLUDED.longitude,
            opening_hours = EXCLUDED.opening_hours,
            updated_at    = EXCLUDED.updated_at
    """

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
    conn.commit()
    logger.info(f"Upserted {len(rows)} stations")

    # Warn if any stations missing geography
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM servo_stations WHERE sa4_name21 IS NULL")
        missing = cur.fetchone()[0]
        if missing:
            logger.warning(f"{missing} stations missing geography — rerun spatial join")


def insert_prices(conn, prices_df: pd.DataFrame) -> None:
    """Bulk insert price records — skip duplicates via ON CONFLICT."""
    now = datetime.now(timezone.utc)

    rows = []
    for _, row in prices_df.iterrows():
        rows.append((
            row["station_id"],
            row["fuel_type"],
            row["is_available"],
            row["price"],
            row["updated_at"],
            now,  # recorded_at
        ))

    sql = """
        INSERT INTO servo_prices
            (station_id, fuel_type, is_available, price, updated_at, recorded_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (station_id, fuel_type, updated_at) DO NOTHING
    """

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
    conn.commit()
    logger.info(f"Inserted prices — {len(rows)} attempted, duplicates skipped")


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def run():
    logger.info("=" * 50)
    logger.info(f"Poller started at {datetime.now(timezone.utc).isoformat()}")

    # 1. Connect to RDS
    conn = get_db_connection()
    logger.info("Connected to RDS")

    try:
        # 2. Fetch from API
        data = fetch_api()

        # 3. Process response
        stations_df, prices_df = process_response(data)
        print(stations_df.head())
        # 4. Upsert stations
        upsert_stations(conn, stations_df.reset_index())

        # 5. Insert prices
        insert_prices(conn, prices_df)

    finally:
        conn.close()
        logger.info("RDS connection closed")

    logger.info("Poller complete")
    logger.info("=" * 50)


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    run()
    return {"statusCode": 200, "body": "Poller complete"}


# Local testing
if __name__ == "__main__":
    run()
