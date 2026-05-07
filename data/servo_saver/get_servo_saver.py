import pandas as pd
import uuid
import requests
import os
import logging
from supabase import create_client
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
 
API_URL          = "https://api.fuel.service.vic.gov.au/open-data/v1/fuel/prices"
 


def fetch_api() -> dict:
    """Fetch current fuel prices from Servo Saver API."""
    headers = {
        "User-Agent":      "PetrolPredictor/1.0",
        "x-consumer-id":   SERVO_SAVER_API,
        "x-transactionid": str(uuid.uuid4()),
    }
    response = requests.get(API_URL, headers=headers, timeout=30)
    response.raise_for_status()
    logger.info(f"API response status: {response.status_code}")
    return response.json()

def process_response(data: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process raw API response into stations and prices DataFrames."""
    
    stations = []
    prices = []

    for item in data['fuelPriceDetails']:
        
        # --- Station ---
        station = item['fuelStation']
        stations.append({
            'id':            station['id'],
            'name':          station['name'],
            'address':       station['address'],
            'brand_id':      station['brandId'],
            'contact_phone': station.get('contactPhone'),  # .get() in case nullable
            'latitude':      station['location']['latitude'],
            'longitude':     station['location']['longitude'],
            'opening_hours': station.get('openingHours'),
        })

        # --- Prices ---
        for price in item['fuelPrices']:
            prices.append({
                'station_id':    station['id'],
                'fuel_type':     price['fuelType'],
                'is_available':  price['isAvailable'],
                'price':         price['price'],
                'updated_at':    price['updatedAt'],
            })

    stations_df = pd.DataFrame(stations).set_index('id')
    prices_df   = pd.DataFrame(prices)

    return stations_df, prices_df



def upsert_stations(supabase, stations_df: pd.DataFrame) -> None:
    """Upsert station records — station details rarely change but can."""
    records = stations_df.reset_index().to_dict(orient='records')
    if not records:
        logger.warning("No station records to upsert — skipping")
        return
    
    # Add updated_at timestamp
    #now = datetime.now(timezone.utc).isoformat()
    #for record in records:
    #    record['updated_at'] = now
 
    try:
        supabase.table("servo_stations").upsert(
            records,
            on_conflict="id"        # update if station id already exists
        ).execute()
        logger.info(f"Upserted {len(records)} stations")
    except Exception as e:
        logger.error(f"Failed to upsert stations: {e}")
        raise

def insert_prices(supabase, prices_df: pd.DataFrame) -> None:
    """Bulk upsert price records. Duplicates silently skipped via ignore_duplicates."""

    now = datetime.now(timezone.utc).isoformat()
    
    # Replace NaN prices with None (NULL in Postgres)
    prices_df['price'] = prices_df['price'].where(prices_df['price'].notna(), None)

    records = prices_df.to_dict(orient='records')
    if prices_df.empty:
        logger.warning("No price records to insert — skipping")
        return
    
    # Replace float NaN with None for JSON serialization
    for record in records:
        record['recorded_at'] = now
        if record['price'] != record['price']:  # NaN check
            record['price'] = None
    

    try:
        supabase.table("servo_prices").upsert(
            records,
            on_conflict="station_id,fuel_type,updated_at",
            returning="minimal",
            ignore_duplicates=True,
        ).execute()
        logger.info(f"Upserted {len(records)} price records")

    except Exception as e:
        logger.error(f"Bulk upsert failed: {e}")
        raise


def main():
    
    SUPABASE_URL     = os.environ["SUPABASE_URL"]
    SUPABASE_KEY     = os.environ["SUPABASE_KEY"]
    SERVO_SAVER_API  = os.environ["SERVO_SAVER_API"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    data = fetch_api()
    stations_df, prices_df = process_response(data)
    upsert_stations(supabase, stations_df)
    insert_prices(supabase, prices_df)


if __name__ == "__main__":
    main()