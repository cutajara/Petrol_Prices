import modeling_functions as mf
import joblib


def train_model():
    dfp = mf.extract_prices()
    dates_list=list(set(dfp['price_date'].astype(str)))
    dfm = mf.extract_markets(dates_list)

    dfm['date'] = dfm['date'].astype(str)
    dfp['price_date'] = dfp['price_date'].astype(str)
    df = dfm.merge(dfp, left_on='date', right_on="price_date", how="left")

    df_feats = mf.features(df)
    #
    model1 = mf.trainmodel(df_feats.copy(), 1)
    model2 = mf.trainmodel(df_feats.copy(), 2)
    model3 = mf.trainmodel(df_feats.copy(), 3)
    #
    training_types = dict(df_feats.drop('price', axis=1).dtypes)

    joblib.dump(training_types, "training_format.pkl")
    joblib.dump(model1, "rf_1day.pkl")
    joblib.dump(model2, "rf_2day.pkl")
    joblib.dump(model3, "rf_3day.pkl")
    
    
if __name__ == '__main__':
    train_model()