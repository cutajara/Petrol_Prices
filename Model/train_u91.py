import joblib
import io
import boto3
from datetime import datetime
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))
import modeling_functions as mf

load_dotenv()

BUCKET_NAME = os.environ['MODEL_BUCKET_NAME']
REGION = os.environ["REGION"]

s3 = boto3.client(
        "s3",
        region_name=REGION,
    )

def upload_model(model, bucket: str, key: str):
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    buffer.seek(0)  # rewind before reading
    s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
    key2=key.replace('.pkl','_') + datetime.now().strftime("%Y%m%d_%H%M%S") + '.pkl'
    s3.put_object(Bucket=bucket, Key=key2, Body=buffer.getvalue())
    

def train_model():
    print("Getting data...")
    dfp = mf.extract_prices()
    dates_list=list(set(dfp['price_date'].astype(str)))
    dfm = mf.extract_markets(dates_list)

    dfm['date'] = dfm['date'].astype(str)
    dfp['price_date'] = dfp['price_date'].astype(str)
    df = dfm.merge(dfp, left_on='date', right_on="price_date", how="left")

    print("Preparing data...")
    df_feats = mf.features(df)
    #
    print("Training models...")
    model1 = mf.trainmodel(df_feats.copy(), 1)
    model2 = mf.trainmodel(df_feats.copy(), 2)
    model3 = mf.trainmodel(df_feats.copy(), 3)
    #
    training_types = dict(df_feats.drop('price', axis=1).dtypes)

    print("Uploading new models...")
    upload_model(training_types, BUCKET_NAME, "u91_training_format.pkl")
    upload_model(model1, BUCKET_NAME, "u91_1day.pkl")
    upload_model(model2, BUCKET_NAME, "u91_2day.pkl")
    upload_model(model3, BUCKET_NAME, "u91_3day.pkl")
    
    #joblib.dump(training_types, "u91_training_format.pkl")
    #joblib.dump(model1, "u91_1day.pkl")
    #joblib.dump(model2, "u91_2day.pkl")
    #joblib.dump(model3, "u91_3day.pkl")
    
def lambda_handler(event, context):
    """AWS Lambda entry point."""
    train_model()
    return {"statusCode": 200, "body": "U91 Model Training Complete"}
    
    
if __name__ == '__main__':
    train_model()