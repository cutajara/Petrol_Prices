mkdir -p package-poller
cp ../data/servo_saver/poller_lambda.py package-poller/
cp ../data/servo_saver/get_servo_saver.py package-poller/    # shared processing functions
cd package-poller
zip -r ../poller-lambda.zip .
cd ..


mkdir -p package-geography
cp ../data/servo_saver/append_station_geo_lambda.py package-geography/
cp ../data/servo_saver/poller_lambda.py package-geography/
cp ../data/servo_saver/append_station_geo.py package-geography/
cd package-geography
zip -r ../geography-lambda.zip .
cd ..

mkdir -p package-market
mkdir -p package-market/market_metrics
mkdir -p package-market/mogas_95
cp ../data/market/market_data_lambda.py package-market/
cp ../data/market/collectMarketData.py package-market/    # shared processing functions
cp ../data/market/market_metrics/marketmetrics.py package-market/market_metrics/   # shared processing functions
cp ../data/market/mogas_95/mogas95.py package-market/mogas_95/   # shared processing functions
cd package-market
zip -r ../market-data-lambda.zip .
cd ..
