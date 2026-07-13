FROM public.ecr.aws/lambda/python:3.11


# 1. Install GCC, Git, and native PROJ system libraries using YUM
RUN yum update -y && \
    yum install -y gcc gcc-c++ make findutils git proj-devel && \
    yum clean all

# 2. Tell the compiler explicitly where the PROJ library lives inside Linux
ENV PROJ_DIR=/usr

# 3. Upgrade Python installation tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install the heavy requirements once
COPY requirements_lambda.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements_lambda.txt

# Copy ALL your lambda python files into the image
COPY data/*.py ${LAMBDA_TASK_ROOT}

# (Optional) Leave a default CMD, but it will be overridden by AWS
CMD [ "extract_pdf.lambda_handler" ]
