# Use the AWS Lambda Python 3.13 base image
FROM public.ecr.aws/lambda/python:3.13

# Example: Copy requirements.txt and install packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target "/opt/python"

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "app.lambda_handler" ]
