FROM public.ecr.aws/lambda/python:3.11


# 3. Upgrade Python installation tools
RUN pip install --no-cache-dir --upgrade pip

# Copy and install the heavy requirements once
COPY requirements_lambda.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements_lambda.txt

# Copy ALL your lambda python files into the image
COPY data/*.py ${LAMBDA_TASK_ROOT}

# (Optional) Leave a default CMD, but it will be overridden by AWS
CMD [ "extract_pdf.lambda_handler" ]
