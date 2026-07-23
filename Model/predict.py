import pandas as pd
import joblib
import modeling_functions as mf


def predict():
    extrafilter = "AND (updated_at AT TIME ZONE 'Australia/Melbourne')::date >= (now() AT TIME ZONE 'Australia/Melbourne')::date - INTERVAL '8 days'"
    dfp = mf.extract_prices(extrafilter)
    dates_list=list(set(dfp['price_date'].astype(str)))
    dfm = mf.extract_markets(dates_list)
    dfm['date'] = dfm['date'].astype(str)
    dfp['price_date'] = dfp['price_date'].astype(str)
    df = dfm.merge(dfp, left_on='date', right_on="price_date", how="left")

    trainingformat = joblib.load('training_format.pkl')
    df_feats = mf.features(df)

    latestprice = df_feats.iloc[-1].price

    df_feats = df_feats[trainingformat.keys()]
    df_feats = df_feats.astype(trainingformat)

    model1 = joblib.load('rf_1day.pkl')
    model2 = joblib.load('rf_2day.pkl')
    model3 = joblib.load('rf_3day.pkl')
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

    dforecast = pd.DataFrame(
        {'forecastdate': [df_feats.iloc[-1].name, df_feats.iloc[-1].name, df_feats.iloc[-1].name],
        'fuel_type': ['U91','U91','U91'],
        'daysforward' : [1, 2, 3],
        'effectivedate' : [day1, day2, day3],
        'price' : [round(latestprice+daychange_1[0],2), round(latestprice+daychange_2[0],2), round(latestprice+daychange_3[0],2)],
        }
    )
    dforecast.to_csv('forecast.csv', mode='a', header=False, index=False)


if __name__ == '__main__':
    predict()