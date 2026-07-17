import psycopg2
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()


SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

RDS_ENDPOINT = os.environ["RDS_ENDPOINT"]
RDS_SECRET = os.environ["RDS_SECRET"]


# Check RDS
rds = psycopg2.connect(
    host=f"{RDS_ENDPOINT}.ap-southeast-2.rds.amazonaws.com",
    port=5432,
    dbname="petrol_predictor",
    user="petrol_admin",
    password=RDS_SECRET,
    sslmode="require"
)
cur = rds.cursor()

cur.execute("""
    SELECT 
        (SELECT COUNT(*) FROM servo_stations) as stations,
        (SELECT COUNT(*) FROM servo_prices)   as prices,
        (SELECT COUNT(*) FROM market_data)    as market,
        (SELECT MAX(recorded_at) FROM servo_prices) as latest_price,
        (SELECT MAX(date) FROM market_data)         as latest_market
""")

print(cur.fetchone())
## Row count by date in RDS
#cur.execute("""
#    SELECT DATE(recorded_at), COUNT(*)
#    FROM servo_prices
#    GROUP BY DATE(recorded_at)
#    ORDER BY DATE(recorded_at)
#""")
#rds_by_date = cur.fetchall()
#print("RDS rows by date:")
#for row in rds_by_date:
#    print(f"  {row[0]}: {row[1]:,}")
#
## Check Supabase
#supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
#result = supabase.table("servo_prices").select("recorded_at", count="exact").execute()
#print(f"\nSupabase total: {result.count:,}")