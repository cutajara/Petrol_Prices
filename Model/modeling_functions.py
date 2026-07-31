import pandas as pd
from datetime import datetime, timezone
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import sys
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))
from query_rds import query_rds

def extract_prices(extrafilter = ""):
    dfp = query_rds(f"""SELECT
        (updated_at AT TIME ZONE 'Australia/Melbourne')::date AS price_date,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS price
    FROM servo_prices
    WHERE fuel_type = 'U91' {extrafilter}
    GROUP BY price_date
    ORDER BY price_date;
            """)


    dfp.loc[pd.to_datetime(dfp["price_date"], utc=True).dt.tz_convert("Australia/Sydney").between(datetime(2026, 5, 1, tzinfo=timezone.utc), datetime(2026, 7, 2, tzinfo=timezone.utc)), 'price'] += 16
    # Change the price on the 3rd of Jul 2026 to 172.9 to reduce the tax noice
    dfp.loc[dfp['price_date'].astype(str)== '2026-07-01','price'] = dfp.loc[dfp['price_date'].astype(str)== '2026-07-01','price']-4
    dfp.loc[dfp['price_date'].astype(str)== '2026-07-02','price'] = dfp.loc[dfp['price_date'].astype(str)== '2026-07-02','price']-5
    dfp.loc[dfp['price_date'].astype(str)== '2026-07-03','price'] = dfp.loc[dfp['price_date'].astype(str)== '2026-07-03','price']+7

    dfp["updated_at_melb_wd"] = pd.to_datetime(dfp["price_date"]).dt.weekday
    return dfp

def extract_markets(dates_list: list):
    dfm = query_rds(f"""SELECT date, metric, value 
            FROM market_data
            WHERE metric IN ('brent_crude','usd_aud') AND 
            date IN ('{"', '".join(dates_list)}')""")
    dfm = dfm.pivot(index="date", columns="metric", values="value").reset_index()
    dfm.ffill(inplace=True) # Fill in missing values with the last known value
    dfm['brent_crude'] = dfm['brent_crude']*dfm['usd_aud'] # Convert to AUD
    return dfm

def features(df: pd.DataFrame) -> pd.DataFrame:
    ### Features
    brent_y = df["brent_crude"]
    for lag in range(1, 8):
        df[f"brent_diff{lag}"] = brent_y - df["brent_crude"].shift(lag)

    df["brent_ma3"]   = brent_y.rolling(3).mean() - brent_y
    #df["brent_ma7"]   = brent_y.rolling(7).mean() - brent_y
    #df["brent_trend"] = brent_y - df["brent_crude"].shift(5)

    # --- U91 price features (differenced) ---
    df["u91_diff1"]    = df["price"].shift(1) - df["price"].shift(2)
    #df["u91_diff2"]    = df["price"].shift(2) - df["price"].shift(3)
    df["u91_momentum"] = df["price"].shift(1) - df["price"].shift(3)


    df["is_weekend"]   = (df["updated_at_melb_wd"] >= 5).astype(int)

    # One-hot encode day of week
    dfdow = pd.get_dummies(df['updated_at_melb_wd'], dtype=int, prefix='dow')

    df = df.merge(dfdow, how = 'inner', left_index=True, right_index=True)

    df.set_index("date", inplace=True)
    drop_cols = ["updated_at_melb_wd", "price_date", "brent_crude", "usd_aud"]

    df.drop(columns=drop_cols, inplace=True)
    return df

def trainmodel(df, days_from_now, n_splits=5):
    df["target"] = (df["price"].shift(-days_from_now) - df["price"])
    df = df.dropna(subset=["price", "target"])

    feature_cols = [c for c in df.columns if c not in ["price", "target"]]
    df = df.dropna(subset=feature_cols)

    df = df.drop(['2026-06-30', '2026-07-01', '2026-07-02',
                  '2026-07-03', '2026-07-04'])

    features = df[feature_cols]
    target   = df["target"]
    print(f"Features shape: {features.shape}, Target shape: {target.shape}")

    model_kwargs = dict(random_state=42, min_samples_split=10,
                         min_samples_leaf=10, n_estimators=500)

    # --- Cross-validated estimate of generalisation error ---
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_mae, baseline_mae = [], []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(features)):
        X_train, X_test = features.iloc[train_idx], features.iloc[test_idx]
        y_train, y_test = target.iloc[train_idx], target.iloc[test_idx]

        fold_model = RandomForestRegressor(**model_kwargs)
        fold_model.fit(X_train, y_train)
        y_pred = fold_model.predict(X_test)

        fold_mae.append(mean_absolute_error(y_test, y_pred))
        # naive baseline: "price won't change" -> predicted diff of 0
        baseline_mae.append(mean_absolute_error(y_test, [0] * len(y_test)))

        print(f"Fold {fold}: n_train={len(train_idx)}, n_test={len(test_idx)}, "
              f"MAE={fold_mae[-1]:.3f}, baseline MAE={baseline_mae[-1]:.3f}")

    print(f"\nMean CV MAE: {sum(fold_mae)/len(fold_mae):.3f}")
    print(f"Mean baseline MAE: {sum(baseline_mae)/len(baseline_mae):.3f}")

    # --- Final model for deployment: fit on ALL available data ---
    model = RandomForestRegressor(**model_kwargs)
    model.fit(features, target)

    #plt.scatter(target, model.predict(features))
    #plt.title(f"In-sample fit, {days_from_now}-day model")
    #plt.show()

    return model