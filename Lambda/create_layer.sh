# Create a directory for the layer
mkdir -p lambda-layer/python

# Install dependencies into it
pip install -r ../requirements_lambda.txt -t lambda-layer/python/

# Zip it up
cd lambda-layer
zip -r ../dependencies-layer.zip python/
cd ..

# Upload to Lambda
aws lambda publish-layer-version \
    --layer-name petrol-predictor-dependencies \
    --zip-file fileb://dependencies-layer.zip \
    --compatible-runtimes python3.11 \
    --region ap-southeast-2