import logging
import os
import json
import boto3
import psycopg2
from datetime import datetime, timezone
import sys
from pathlib import Path
MARKET_DIR = Path(__file__).resolve().parent
if str(MARKET_DIR) not in sys.path:
    sys.path.insert(0, str(MARKET_DIR))

from collectMarketData import collectMarketData

# --- Logging ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Config ---
AURORA_ENDPOINT = os.environ["AURORA_ENDPOINT"]
REGION = os.environ["REGION"]
AURORA_DB = os.environ["AURORA_DB"]
AURORA_USER = os.environ["AURORA_USER"]
AURORA_HOST= f"{AURORA_DB}.{AURORA_ENDPOINT}.{REGION}.rds.amazonaws.com"

# ---------------------------------------------------------------
# Database
# ---------------------------------------------------------------

def get_iam_token() -> str:
    """Generate IAM auth token for Aurora."""
    client = boto3.client("rds", region_name=REGION)
    return client.generate_db_auth_token(
        DBHostname=AURORA_HOST,
        Port=5432,
        DBUsername=AURORA_USER,
        Region=REGION,
    )


def get_db_connection():
    """Get a psycopg2 connection using IAM."""
    return psycopg2.connect(
        host=AURORA_HOST,
        port=5432,
        #dbname=AURORA_DB,
        database='postgres',
        user=AURORA_USER,
        password=get_iam_token(),
        sslmode="require",
        connect_timeout=300,
    )


# ---------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------

def already_stored(cur, metric: str, date: str) -> bool:
    """Check if we already have a record for this metric + date."""
    cur.execute(
        "SELECT id FROM market_data WHERE metric = %s AND date = %s",
        (metric, date)
    )
    return cur.fetchone() is not None


def insert_metric(cur, metric: str, value: float, date: str) -> None:
    """Insert a market data record."""
    cur.execute(
        """
        INSERT INTO market_data (metric, value, date, polled_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (metric, date) DO NOTHING
        """,
        (metric, value, date, datetime.now(timezone.utc))
    )


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def run():
    logger.info("=" * 50)
    logger.info(f"Market data fetch started at {datetime.now(timezone.utc).isoformat()}")

    conn = get_db_connection()
    logger.info("Connected to RDS")
    
    todays_data_list = collectMarketData() # Get the data

    try:
        with conn.cursor() as cur:
            for record in todays_data_list:
                try:

                    if already_stored(cur, record['metric'], record["date"]):
                        logger.info(f"  Already have {record['metric']} for {record['date']} — skipping")
                        continue

                    insert_metric(cur, record['metric'], record["value"], record["date"])
                    logger.info(f"  Inserted {record['metric']}: {record['value']} for {record['date']}")

                except Exception as e:
                    logger.error(f"  Error fetching {record['metric']}: {e}")

        conn.commit()

    finally:
        conn.close()
        logger.info("RDS connection closed")

    logger.info("Market data fetch complete")
    logger.info("=" * 50)


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    run()
    return {"statusCode": 200, "body": "Market data fetch complete"}


# Local testing
if __name__ == "__main__":
    run()
