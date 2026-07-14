FROM public.ecr.aws/lambda/python:3.12

# Upgrade core pip installation tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install your heavy Python dependencies 
COPY requirements_lambda.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements_lambda.txt

# Copy ALL your lambda python files into the image at once
COPY *.py ${LAMBDA_TASK_ROOT}

# Fallback default entry point (Overridden by your individual AWS Lambda CMD settings)
CMD [ "extract_pdf.lambda_handler" ]
