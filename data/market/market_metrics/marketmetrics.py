import yfinance as yf
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Get close price of Brent crude oil
def fetch_latest(ticker_symbol: str) -> dict:
    """
    Uses yfinance to fetch the latest close price for a given ticker symbol. Returns the price and the date of the close price.

    Args:
        ticker_symbol (str): Metric ticker symbol to fetch the latest price for (e.g. "BZ=F" for Brent crude oil)

    Returns:
        tuple: A tuple containing the latest price (float) and the date of the close price (str in YYYY-MM-DD format)
    """
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="3d")
    if hist.empty:
        logger.error(f"No data for {ticker_symbol}")
        raise ValueError(f"No data for {ticker_symbol}")
    return round(float(hist["Close"].iloc[-1]), 4), hist.index[-1].date().isoformat()