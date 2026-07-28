import os
import logging
import pandas as pd
import sys
from pathlib import Path
MARKET_DIR = Path(__file__).resolve().parent
if str(MARKET_DIR) not in sys.path:
    sys.path.insert(0, str(MARKET_DIR))
    
from append_station_geo import download_abs_meshblockdata, append_geographic_info
from poller_lambda import get_db_connection

# --- Logging ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Config ---
SECRET_NAME = os.environ.get("SECRET_NAME", "petrol-predictor/rds")


def read_stations(conn):
    sql = """
    SELECT id, latitude, longitude
    FROM servo_stations
    WHERE mb_code21 IS NULL
    """
    
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        cols = ["id", "latitude", "longitude"]
 
    df = pd.DataFrame(rows, columns=cols)
    logger.info(f"Found {len(df)} stations missing geography")
    return df

def update_stations(conn, geography_df: pd.DataFrame) -> None:
    """Write geography columns back to servo_stations."""
    if geography_df.empty:
        logger.info("No stations to update")
        return
 
    sql = """
        UPDATE servo_stations
        SET mb_code21  = %s,
            gcc_name21 = %s,
            sa4_name21 = %s,
            updated_at = now()
        WHERE id = %s
    """
 
    rows = [
        (row.mb_code21, row.gcc_name21, row.sa4_name21, row.id)
        for _, row in geography_df.iterrows()
        if pd.notna(row.sa4_name21)  # only update if join succeeded
    ]
 
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
 
    logger.info(f"Updated {len(rows)} stations with geography")

def run():
    logger.info("=" * 50)
    logger.info("Checking for new servo stations")
    
    # 1. Connect to RDS
    conn = get_db_connection()
    logger.info("Connected to RDS")
    
    try:
        stations_df = read_stations(conn)
        
        if stations_df.empty:
            logger.info("All stations have geography assigned — nothing to do")
            return

        meshblock = download_abs_meshblockdata()
        
        geography_df = append_geographic_info(stations_df,meshblock)
        
        update_stations(conn, geography_df) 
    
    finally:
        conn.close()
        logger.info("RDS connection closed")






def lambda_handler(event, context):
    """AWS Lambda entry point."""
    run()
    return {"statusCode": 200, "body": "Poller complete"}


# Local testing
if __name__ == "__main__":
    run()