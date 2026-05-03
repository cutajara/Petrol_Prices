import yfinance as yf
# Get close price of Brent crude oil
def fetch_latest(ticker_symbol: str) -> dict:
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="3d")
    if hist.empty:
        raise ValueError(f"No data for {ticker_symbol}")
    return round(float(hist["Close"].iloc[-1]), 4), hist.index[-1].date().isoformat()

def request_market_data(code):
    close_price, close_day = fetch_latest(code)
#    close_day_utc = close_day.tz_convert("UTC")
    return close_price, close_day
