import streamlit as st
import pandas as pd
import modeling_functions as mf
import plotly.graph_objects as go

st.set_page_config(
    page_title="Victorian Petrol Price Forecast",
    page_icon="⛽",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1300px;
    }
    .stMetric {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        padding: 0.7rem 0.8rem;
    }
    
    div[data-testid="stMetric"] * {
        color: black !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



st.title("Victorian Petrol Price Forecast")
st.subheader("Should you fill up today, or wait?")
st.markdown("Ever wondered if you waited a day to two, could to refuel you car cheaper? "
            "This project aims to take the 'gamble' element out of when to fill up your car, by using Machine Learning to forecast the next 3 days prices. The forecast of U91 (atm) uses the [VIC Servo Saver API](https://service.vic.gov.au/find-services/transport-and-driving/servo-saver) and financial market data.")

extrafilter = "AND (updated_at AT TIME ZONE 'Australia/Melbourne')::date >= (now() AT TIME ZONE 'Australia/Melbourne')::date - INTERVAL '28 days'"
dfp = mf.extract_prices(extrafilter)
dates_list=list(set(dfp['price_date'].astype(str)))
dfm = mf.extract_markets(dates_list)

dfm['date'] = dfm['date'].astype(str)
dfp['price_date'] = dfp['price_date'].astype(str)
df = dfm.merge(dfp, left_on='date', right_on="price_date", how="left")
dforecast = pd.read_csv('forecast.csv')
dforecast = dforecast.loc[dforecast['fuel_type']=='U91',:]
dforecast = dforecast.rename(columns={'effectivedate': 'date'})
df = df.merge(dforecast, how ='outer', suffixes=['', '_forecast'], on='date')
df.loc[df['date']==dforecast['forecastdate'].values[0], 'price_forecast'] = df.loc[df['date']==dforecast['forecastdate'].values[0], 'price']


latest_price = df["price"].dropna().iloc[-1]
latest_forecast = df["price_forecast"].dropna().iloc[-1]
latest_brent = df["brent_crude"].dropna().iloc[-1]


col1, col2, col3 = st.columns(3)
col1.metric("Latest observed price", f"${latest_price:.2f}")
col2.metric("Latest forecast", f"${latest_forecast:.2f}")
col3.metric("Latest Brent value", f"{latest_brent:.2f}")

st.subheader("Price forecast")
#st.line_chart(df, x="date", y=["price",'brent_crude', "price_forecast"])

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df["date"],
        y=df["price"],
        mode="lines",
        name="price",
        line=dict(color="#2563eb", width=2),
        yaxis="y",
    )
)

fig.add_trace(
    go.Scatter(
        x=df["date"],
        y=df["brent_crude"],
        mode="lines",
        name="Brent Crude (AUD)",
        line=dict(color="#15db36", width=2),
        yaxis="y2",
    )
)

fig.add_trace(
    go.Scatter(
        x=df["date"],
        y=df["price_forecast"],
        mode="lines",
        name="price_forecast",
        line=dict(color="#f59e0b", width=2, dash="dash"),
        yaxis="y",
    )
)
fig.update_layout(
    yaxis=dict(title="Price"),
    yaxis2=dict(title="Brent Crude (AUD)", overlaying="y", side="right"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5
    )
)

st.plotly_chart(fig, use_container_width=True)