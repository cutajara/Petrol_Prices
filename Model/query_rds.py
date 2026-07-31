import os
import pandas as pd
import psycopg2
import boto3
from dotenv import load_dotenv
load_dotenv()

AURORA_ENDPOINT = os.environ["AURORA_ENDPOINT"]
REGION = os.environ["REGION"]
AURORA_DB = os.environ["AURORA_DB"]
AURORA_USER = os.environ["AURORA_USER"]

AURORA_HOST= f"{AURORA_DB}.{AURORA_ENDPOINT}.{REGION}.rds.amazonaws.com"

def get_iam_token() -> str:
    """Generate IAM auth token for Aurora."""
    client = boto3.client("rds", region_name=REGION)
    return client.generate_db_auth_token(
        DBHostname=AURORA_HOST,
        Port=5432,
        DBUsername=AURORA_USER,
        Region=REGION,
    )


def connect_rds():
    return psycopg2.connect(
        host=AURORA_HOST,
        port=5432,
        #dbname=AURORA_DB,
        database='postgres',
        user=AURORA_USER,
        password=get_iam_token(),
        sslmode="require",
        connect_timeout=10,
    )

def query_rds(sql):

    # Check RDS
    rds = connect_rds()
    cur = rds.cursor()

    cur.execute(sql)

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    cur.close()
    rds.close()

    return pd.DataFrame(rows, columns=columns)

