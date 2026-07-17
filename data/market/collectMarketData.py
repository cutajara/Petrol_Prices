import datetime
from datetime import timezone
from supabase import create_client
import os
import logging
import sys
from pathlib import Path
MARKET_DIR = Path(__file__).resolve().parent
if str(MARKET_DIR) not in sys.path:
    sys.path.insert(0, str(MARKET_DIR))
import market_metrics.marketmetrics as mm
import mogas_95.mogas95 as m95

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def collectMarketData():
    """
    Get the latest market data for key Petrol metrics
    
    Returns:
        list: A list of dictionaries containing the latest market data for key Petrol metrics
    """
    request_time = datetime.datetime.now(timezone.utc).isoformat()
    metrics = ["BZ=F", "USDAUD=X", "DX-Y.NYB"]
    labels = ["brent_crude", "usd_aud", "dxy"]
    
    market_data = []
    for metric, label in zip(metrics, labels):
        try:
            price, close_timestamp = mm.fetch_latest(metric)
            market_data.append({"metric" :label, "value": price, "date": close_timestamp, "polled_at": request_time})           
        except Exception as e:
            logger.error(f"Error fetching data for {metric}: {e}")

#    if datetime.datetime.now().weekday() == 0:  # If today is MOnday, fetch the latest AIP report
    try:
        mogas_95_price, mogas_95_date = m95.extract_mogas_95()
        market_data.append({"metric" : "mogas_95", "value": mogas_95_price, "date": mogas_95_date, "polled_at": request_time})
    except Exception as e:
        logger.error(f"Error fetching data for mogas_95: {e}")
    
    return market_data


def already_stored_check(supabase, table: str, date, metric) -> bool:
    """Rule to check if a record for the given date and metric already exists in the database
    Args:
        supabase: Supabase client instance
        table (str): The name of the table to check
        date (YYY-MM-DD): The date to check for
        metric (str): The metric to check for
        
    """
    result = supabase.table(table).select("id").eq("date", date).eq("metric", metric).execute()
    return len(result.data) == 0


def update_market_data_table():
    todays_data_list = collectMarketData() # Get the data

    SUPABASE_URL = os.environ["SUPABASE_URL"]
    SUPABASE_KEY = os.environ["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    for record in todays_data_list:
        try:
            if already_stored_check(supabase, "market_data", record["date"], record["metric"]):
                supabase.table("market_data").insert(record).execute()
        except Exception as e:
            logger.error(f"Error inserting record for {record['metric']} on {record['date']}: {e}")
        else:
            logging.warning(f"Record for {record['metric']} on {record['date']} already exists. Skipping.")
            
if __name__ == "__main__":
    update_market_data_table()