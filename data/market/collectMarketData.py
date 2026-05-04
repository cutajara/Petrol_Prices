import market_metrics.marketmetrics as mm
import mogas_95.mogas95 as m95
import datetime
from datetime import timezone
from supabase import create_client
import os


def collectMarketData():

    request_time = datetime.datetime.now(timezone.utc).isoformat()
    metrics = ["BZ=F", "USDAUD=X", "DX-Y.NYB"]
    labels = ["brent_crude", "usd_aud", "dxy"]
    
    market_data = []
    for metric, label in zip(metrics, labels):
        price, close_timestamp = mm.request_market_data(metric)
        market_data.append({"metric" :label, "value": price, "date": close_timestamp, "polled_at": request_time})
        
#    if datetime.datetime.now().weekday() == 0:  # If today is MOnday, fetch the latest AIP report
    mogas_95_price, mogas_95_date = m95.extract_mogas_95()
    market_data.append({"metric" : "mogas_95", "value": mogas_95_price, "date": mogas_95_date, "polled_at": request_time})
    
    return market_data


def already_stored_check(supabase, table: str, date, metric) -> bool:
    result = supabase.table(table).select("id").eq("date", date).eq("metric", metric).execute()
    return len(result.data) == 0


def update_market_data_table():
    todays_data_list = collectMarketData()

    SUPABASE_URL = os.environ["SUPABASE_URL"]
    SUPABASE_KEY = os.environ["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    for record in todays_data_list:
        if already_stored_check(supabase, "market_data", record["date"], record["metric"]):
            supabase.table("market_data").insert(record).execute()
        else:
            print(f"Record for {record['metric']} on {record['date']} already exists. Skipping.")
            
if __name__ == "__main__":
    update_market_data_table()