import pandas as pd
import joblib
import modeling_functions as mf
import os
import io
import boto3
from query_rds import connect_rds
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

BUCKET_NAME = os.environ['MODEL_BUCKET_NAME']
REGION = os.environ["REGION"]

s3 = boto3.client(
        "s3",
        region_name=REGION,
    )

def download_model(s3, bucket: str, key):
    
    obj = s3.get_object(Bucket=bucket, Key=key)
    model = joblib.load(io.BytesIO(obj["Body"].read()))

    return model

def predict():
    extrafilter = "AND (updated_at AT TIME ZONE 'Australia/Melbourne')::date >= (now() AT TIME ZONE 'Australia/Melbourne')::date - INTERVAL '8 days'"
    dfp = mf.extract_prices(extrafilter)
    dates_list=list(set(dfp['price_date'].astype(str)))
    dfm = mf.extract_markets(dates_list)
    dfm['date'] = dfm['date'].astype(str)
    dfp['price_date'] = dfp['price_date'].astype(str)
    df = dfm.merge(dfp, left_on='date', right_on="price_date", how="outer")
    df.loc[df['date'].isna(),'date'] = df.loc[df['date'].isna(),'price_date']
    df.loc[df['price_date'].isna(),'price_date'] = df.loc[df['price_date'].isna(),'date']
    df['brent_crude'] = df['brent_crude'].ffill() # Fill in missing values with the last known value
    df['usd_aud'] = df['usd_aud'].ffill() # Fill in missing values with the last known value
    df['price'] = df['price'].ffill() # Fill in missing values with the last known value
    
    #trainingformat = joblib.load('u91_training_format.pkl')
    trainingformat = download_model(s3, BUCKET_NAME, 'u91_training_format.pkl')
    df_feats = mf.features(df)

    latestprice = df_feats.iloc[-1].price
    print(f"The latest day in from the servo saver is {df_feats.iloc[-1].name}")

    df_feats = df_feats[trainingformat.keys()]
    df_feats = df_feats.astype(trainingformat)

    model1 = download_model(s3, BUCKET_NAME, 'u91_1day.pkl')
    model2 = download_model(s3, BUCKET_NAME, 'u91_2day.pkl')
    model3 = download_model(s3, BUCKET_NAME, 'u91_3day.pkl')
    #model1 = joblib.load('u91_1day.pkl')
    #model2 = joblib.load('u91_2day.pkl')
    #model3 = joblib.load('u91_3day.pkl')
    daychange_1 = model1.predict(pd.DataFrame(df_feats.iloc[-1]).T)
    daychange_2 = model2.predict(pd.DataFrame(df_feats.iloc[-1]).T)
    daychange_3 = model3.predict(pd.DataFrame(df_feats.iloc[-1]).T)

    day1 = (pd.to_datetime(df_feats.iloc[-1].name) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    day2 = (pd.to_datetime(df_feats.iloc[-1].name) + pd.Timedelta(days=2)).strftime('%Y-%m-%d')
    day3 = (pd.to_datetime(df_feats.iloc[-1].name) + pd.Timedelta(days=3)).strftime('%Y-%m-%d')

    print(df_feats.iloc[-1].name, latestprice)
    print(day1, daychange_1[0], latestprice+daychange_1[0])
    print(day2, daychange_2[0], latestprice+daychange_2[0])
    print(day3, daychange_3[0], latestprice+daychange_3[0])


    sql = """
            INSERT INTO forecasts
                (forecastdate, fuel_type, daysforward, effectivedate,
                 price, forecasted_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (forecastdate, fuel_type, daysforward) DO UPDATE SET
                forecastdate    = EXCLUDED.forecastdate,
                fuel_type       = EXCLUDED.fuel_type,
                daysforward     = EXCLUDED.daysforward,
                effectivedate   = EXCLUDED.effectivedate,
                price           = EXCLUDED.price,
                forecasted_at   = EXCLUDED.forecasted_at
        """
    now = datetime.now(timezone.utc)
    rows = [
        (df_feats.iloc[-1].name, 'U91', 1, day1, round(float(latestprice+daychange_1[0]),2), now),
        (df_feats.iloc[-1].name, 'U91', 2, day2, round(float(latestprice+daychange_2[0]),2), now),
        (df_feats.iloc[-1].name, 'U91', 3, day3, round(float(latestprice+daychange_3[0]),2),now)
    ]


    conn = connect_rds()
    
    with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
    conn.commit()
    print(f"Upserted {len(rows)} stations")

    #dforecast = pd.DataFrame(
    #    {'forecastdate': [df_feats.iloc[-1].name, df_feats.iloc[-1].name, df_feats.iloc[-1].name],
    #    'fuel_type': ['U91','U91','U91'],
    #    'daysforward' : [1, 2, 3],
    #    'effectivedate' : [day1, day2, day3],
    #    'price' : [round(latestprice+daychange_1[0],2), round(latestprice+daychange_2[0],2), round(latestprice+daychange_3[0],2)],
    #    }
    #)
    #dforecast.to_csv('forecast.csv', mode='a', header=False, index=False)


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    predict()
    return {"statusCode": 200, "body": "U91 Prediction Complete"}



if __name__ == '__main__':
    predict()