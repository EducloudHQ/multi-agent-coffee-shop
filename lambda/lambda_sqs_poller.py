import json
import boto3
import os

def handler(event, context):
    # Log the event for debugging
    print("Received event: " + json.dumps(event))

    # Initialize SQS and Bedrock clients
    sqs_client = boto3.client('sqs')
    bedrock_client = boto3.client('bedrock-runtime')

    # Get the SQS queue URL and Bedrock inference profile ARN from environment variables
    sqs_queue_url = os.environ["SQS_QUEUE_URL"]


    # Process each message in the event
    for record in event['Records']:
        message_body = json.loads(record['body'])
        print("Processing message:", message_body)

        # Extract the text from the message
        extracted_text = message_body['text']

        # Use the Bedrock foundation model to manipulate the text
        # Use the Bedrock foundation model to extract a grocery list
        prompt = f"""You are a helpful assistant that extracts grocery items alongside their amount in kg and count if available, from text. 
        If the text contains a grocery list, respond with ONLY the list of items alongside their amount in kg and count if available in the following format:
        - Item 1, kg, count
        - Item 2,kg, count
        - Item 3,kg, count

        If the text does NOT contain a grocery list, respond with: "No grocery list found."

        Here is the text:
        {extracted_text}"""
        response = bedrock_client.invoke_model(

            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",  # Use the correct model ID
            body=json.dumps({
                "messages": [
                    {
                        "role": "user",  # The role of the message (user or assistant)
                        "content": prompt  # The actual prompt
                    }
                ],
                "max_tokens": 300,  # Maximum number of tokens to generate
                "temperature": 0.7,  # Controls randomness (0 = deterministic, 1 = creative)
                "top_p": 0.9,  # Controls diversity (0 = narrow, 1 = diverse)
                "anthropic_version": "bedrock-2023-05-31"  # Required for Claude 3 models
            })
        )
 # Parse the response from Bedrock
        response_body = json.loads(response['body'].read())
        manipulated_text = response_body['content'][0]['text']  # Extract the generated text

        # Check if the response contains a grocery list or a "No grocery list found" message
        if "No grocery list found." in manipulated_text:
            print("No grocery list found in the extracted text.")
        else:
            print("Grocery List:\n", manipulated_text)

        # Delete the message from the queue after processing
        receipt_handle = record['receiptHandle']
        sqs_client.delete_message(
            QueueUrl=sqs_queue_url,
            ReceiptHandle=receipt_handle
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Message processing complete!')
    }