import json
import boto3
import os
from urllib.parse import unquote_plus


def handler(event, context):
    # Log the event for debugging
    print("Received event: " + json.dumps(event))

    # Initialize Textract, S3, and SQS clients
    textract = boto3.client('textract',region_name='us-east-1')
    s3_client = boto3.client('s3',region_name='us-east-1')
    sqs_client = boto3.client('sqs')

    # Get the SQS queue URL from the environment variable
    sqs_queue_url = os.environ["SQS_QUEUE_URL"]

    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        object_key = unquote_plus(record['s3']['object']['key'])  # Decode the object key

        print(f"Processing file from bucket: {bucket_name}, key: {object_key}")

        # Get the file type
        file_extension = object_key.split('.')[-1].lower()

        # Handle PDF files
        if file_extension == 'pdf':
            print("PDF file detected. Converting to JPEG...")
            jpeg_key = convert_pdf_to_jpeg(s3_client, bucket_name, object_key)
            if not jpeg_key:
                print("Failed to convert PDF to JPEG.")
                continue
            object_key = jpeg_key  # Update the object key to the converted JPEG file

        # Extract text using Textract
        detected_text = extract_text_from_file(textract, bucket_name, object_key)
        if not detected_text:
            print("No text detected in the file.")
            continue

        print("Detected Text:\n", detected_text)

        # Send the detected text to the SQS queue
        sqs_client.send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=json.dumps({
                "text": detected_text,
                "bucket": bucket_name,
                "key": object_key
            })
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Text extraction and SQS sending complete!')
    }


def convert_pdf_to_jpeg(s3_client, bucket_name, pdf_key):
    """
    Converts a PDF file to JPEG using Amazon Textract.
    Returns the S3 key of the converted JPEG file.

    """

    print(f"Bucket name here is {bucket_name}")
    print(f"Keys here is {pdf_key}")
    try:
        # Use Textract to convert PDF to JPEG
        textract = boto3.client('textract',region_name='us-east-1')
        response = textract.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': pdf_key
                }
            },
            OutputConfig={
                'S3Bucket': bucket_name,
                'S3Prefix': 'converted/'
            }
        )

        # Wait for the conversion to complete
        job_id = response['JobId']
        print(f"Started Textract job for PDF conversion: {job_id}")

        # Poll for job completion (simplified for demonstration)
        while True:
            status = textract.get_document_text_detection(JobId=job_id)
            if status['JobStatus'] in ['SUCCEEDED', 'FAILED']:
                break

        if status['JobStatus'] == 'FAILED':
            print("PDF to JPEG conversion failed.")
            return None

        # Get the output JPEG file key
        jpeg_key = status['DocumentLocation']['S3Object']['Name']
        print(f"PDF converted to JPEG: {jpeg_key}")
        return jpeg_key

    except Exception as e:
        print(f"Error converting PDF to JPEG: {e}")
        return None


def extract_text_from_file(textract, bucket_name, object_key):
    """
    Extracts text from a file (JPEG or PDF) using Amazon Textract.
    Returns the extracted text as a string.
    """
    try:
        response = textract.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': object_key
                }
            }
        )

        # Extract the detected text
        detected_text = ""
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                detected_text += item['Text'] + "\n"

        return detected_text

    except Exception as e:
        print(f"Error extracting text from file: {e}")
        return None
