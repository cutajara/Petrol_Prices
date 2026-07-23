import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

RDS_ENDPOINT = os.environ["RDS_ENDPOINT"]
RDS_SECRET = os.environ["RDS_SECRET"]


def query_rds(sql):

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

    cur.execute(sql)

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    cur.close()
    rds.close()

    return pd.DataFrame(rows, columns=columns)

