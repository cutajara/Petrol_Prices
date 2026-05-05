import requests
import pdfplumber
from io import BytesIO
import datetime
from datetime import timedelta
import pandas as pd
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

def find_last_sunday():
    """Find the number of days to subtract to get to the most recent Sunday. if today is Sunday, returns 7 to get the previous Sunday."""
    today = datetime.datetime.now().weekday()
    days = (today+1) % 7
    if days == 0:
        days = 7
    return days

def get_latest_aip_report_url(daydelay: int) -> str:
    """Build URL for the most recent Sunday AIP report."""
    # AIP publishes on Sundays — find the last Sunday
    today = datetime.datetime.now() - timedelta(days=daydelay)  # Ensure we get last Sunday's report even if today is Sunday
    days_since_sunday = today.weekday() + 1  # Monday=0, so Sunday=-1 mod 7
    last_sunday = today - timedelta(days=days_since_sunday % 7)
    
    month_str = last_sunday.strftime("%Y-%m")
    # Use %d and strip leading zero for cross-platform compatibility
    date_str = last_sunday.strftime("%d %B %Y").lstrip("0")  # e.g. "5 April 2026"
    
    return (
        f"https://www.aip.com.au/sites/default/files/download-files/"
        f"{month_str}/Weekly%20Petrol%20Prices%20Report%20-%20{date_str.replace(' ', '%20')}.pdf"
    )  
    
def extract_mogas_95_price_from_pdf(response) -> str:
    with pdfplumber.open(BytesIO(response.content)) as pdf:
        first_page = pdf.pages[3]
        tables = first_page.extract_tables()
        
        if not tables:
            logger.error("No tables found on page")
            return None
        
        # Inspect the first table
        first_table = tables[0]
        mogas_95 = first_table[0][1].split("Average")[0].strip()
        return first_table[0][0], mogas_95
    
    
def extract_mogas_95():
    daydelay = find_last_sunday()
    report_url = get_latest_aip_report_url(daydelay)

    response = requests.get(report_url, timeout=15)
        
    if response.status_code != 200:
        raise ValueError(f"Could not fetch AIP report: {report_url}")
                
    mogas_95_label, mogas_95_price = extract_mogas_95_price_from_pdf(response)
    match = re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", mogas_95_label)
    mogas_95_date = match.group(0) if match else None
    mogas_95_date = pd.to_datetime(mogas_95_date, dayfirst=True).strftime('%Y-%m-%d') # Perfor wranglings to get the date of the price
    return float(mogas_95_price), mogas_95_date