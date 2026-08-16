import streamlit as st
import pandas as pd
import modeling_functions as mf
import plotly.graph_objects as go
from query_rds import query_rds

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
st.markdown("Ever wondered if you waited a day to two, could to refuel your car cheaper? "
            "This project aims to take the 'gamble' element out of when to fill up your car, by using Machine Learning to forecast the next 6 days prices. The forecast of U91 uses the [VIC Servo Saver API](https://service.vic.gov.au/find-services/transport-and-driving/servo-saver) and financial market data.")

extrafilter = "AND (updated_at AT TIME ZONE 'Australia/Melbourne')::date >= (now() AT TIME ZONE 'Australia/Melbourne')::date - INTERVAL '28 days'"
with st.spinner("Awaking Aurora..."):
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

latestday = df.iloc[-1,:]['date']

#dforecast = pd.read_csv('forecast.csv')
#dforecast = dforecast.loc[dforecast['fuel_type']=='U91',:]
#dforecast = dforecast.loc[dforecast['forecastdate']==latestday,:]
#dforecast = dforecast.rename(columns={'effectivedate': 'date'})

dforecast = query_rds(f"SELECT forecastdate, price, effectivedate as date FROM forecasts WHERE fuel_type = 'U91' AND forecastdate = '{latestday}'")
forecast_available = not dforecast.empty
if forecast_available:
    dforecast['date'] = dforecast['date'].astype(str)
    dforecast['forecastdate'] = dforecast['forecastdate'].astype(str)

    df = df.merge(dforecast, how='outer', suffixes=['', '_forecast'], on='date')
    latest_forecast_date = dforecast['forecastdate'].dropna().iloc[0]
    df.loc[df['date'] == latest_forecast_date, 'price_forecast'] = df.loc[df['date'] == latest_forecast_date, 'price']
else:
    df = df.copy()

latest_price = df["price"].dropna().iloc[-1]
latest_brent = df["brent_crude"].dropna().iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("Latest observed price", f"{latest_price:.2f}c/L")
if forecast_available:
    latest_forecast = df["price_forecast"].dropna().iloc[-1]
    col2.metric("Latest forecast", f"{latest_forecast:.2f}c/L")
else:
    col2.warning("No forecast available")
col3.metric("Latest Brent value", f"${latest_brent:.2f} AUD/barrel")

st.subheader("Price Forecast")
button_label = "Display Previous 5 days Forecasts"
monitor_model = st.toggle(button_label)

#st.line_chart(df, x="date", y=["price",'brent_crude', "price_forecast"])

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df["date"],
        y=df["price"],
        mode="lines",
        name="Price (c/L)",
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

if forecast_available:
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["price_forecast"],
            mode="lines",
            name="Latest forecast",
            line=dict(color="#f59e0b", width=2, dash="dash"),
            yaxis="y",
        )
    )
else:
    st.info("No forecast exists for the latest day yet, so no forecast trace is available to plot.")

if monitor_model:
    recent_forecasts = query_rds(
        """
        SELECT forecastdate, effectivedate::date AS date, price
        FROM forecasts
        WHERE fuel_type = 'U91'
          AND forecastdate >= (CURRENT_DATE - INTERVAL '5 days')::date
        ORDER BY forecastdate, effectivedate
        """
    )
    if not recent_forecasts.empty:
        recent_forecasts['date'] = pd.to_datetime(recent_forecasts['date']).dt.strftime('%Y-%m-%d')
        recent_forecasts['forecastdate'] = pd.to_datetime(recent_forecasts['forecastdate']).dt.strftime('%Y-%m-%d')

        actual_prices = (
            df[['date', 'price']]
            .dropna(subset=['date', 'price'])
            .drop_duplicates()
            .rename(columns={'date': 'forecastdate', 'price': 'actual_price'})
        )
        recent_forecasts = recent_forecasts.merge(actual_prices, on='forecastdate', how='left')

        forecast_colors = [
            '#ef4444', '#8b5cf6', '#06b6d4', '#22c55e', "#6d7411",
            '#ec4899', '#14b8a6', '#f97316'
        ]

        for idx, (forecastdate, group) in enumerate(recent_forecasts.groupby('forecastdate', sort=True)):
            anchor_point = pd.DataFrame({
                'date': [forecastdate],
                'price': [group['actual_price'].iloc[0]],
            })
            forecast_line = pd.concat([anchor_point, group[['date', 'price']]], ignore_index=True)
            forecast_line = forecast_line.sort_values('date')

            fig.add_trace(
                go.Scatter(
                    x=forecast_line['date'],
                    y=forecast_line['price'],
                    mode='lines',
                    name=f'Forecast {forecastdate}',
                    line=dict(color=forecast_colors[idx % len(forecast_colors)], width=2 ,dash="dash"),
                    marker=dict(size=7, color=forecast_colors[idx % len(forecast_colors)]),
                    opacity=0.6,
                    yaxis='y',
                )
            )

fig.update_layout(
    yaxis=dict(title="Price (c/L)"),
    yaxis2=dict(title="Brent Crude (AUD)", overlaying="y", side="right"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5
    )
)


st.plotly_chart(
    fig,
    use_container_width=True,
    config={"responsive": True, "displayModeBar": False},
)