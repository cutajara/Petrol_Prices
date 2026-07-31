FROM public.ecr.aws/lambda/python:3.12

# Upgrade core pip installation tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install your heavy Python dependencies 
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL your lambda python files into the image at once
COPY . ${LAMBDA_TASK_ROOT}

# Fallback default entry point (Overridden by your individual AWS Lambda CMD settings)
CMD [ "data.servo_saver.poller_lambda.lambda_handler" ]
