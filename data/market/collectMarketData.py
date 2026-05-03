import market.market_metrics.marketmetrics as mm
import market.mogas_95.mogas95 as m95
import datetime
from datetime import timezone

def collectMarketData():

    request_time = datetime.datetime.now(timezone.utc).isoformat()
    metrics = ["BZ=F", "USDAUD=X", "DX-Y.NYB"]
    labels = ["brent_crude", "usd_aud", "dxy"]
    
    market_data = []
    for metric, label in zip(metrics, labels):
        price, close_timestamp = mm.request_market_data(metric)
        market_data.append({"metric" :label, "value": price, "date": close_timestamp, "polled_at": request_time})
        
    if datetime.datetime.now().weekday() == 0:  # If today is MOnday, fetch the latest AIP report
        mogas_95_price, mogas_95_date = m95.extract_mogas_95()
        market_data.append({"metric" : "mogas_95", "value": mogas_95_price, "date": mogas_95_date, "polled_at": request_time})
    
    return market_data