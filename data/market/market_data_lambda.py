import logging
import os
import json
import boto3
import psycopg2
from datetime import datetime, timezone
from collectMarketData import collectMarketData

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- Config ---
SECRET_NAME = os.environ.get("SECRET_NAME", "petrol-predictor/rds")
RDS_ENDPOINT = os.environ.get("RDS_ENDPOINT", "petrol-predictor/rds")

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
