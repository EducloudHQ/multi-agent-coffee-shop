
from aws_cdk import (
    Stack, Aws, Duration, CfnOutput,
)

from aws_cdk import (aws_lambda, aws_s3, aws_s3_notifications, aws_iam as iam,aws_lambda_event_sources as lambda_event_sources,
                     aws_appsync as appsync, aws_sqs as sqs, aws_dynamodb as dynamodb )
from aws_cdk.aws_appsync import SchemaFile

from aws_cdk.aws_lambda import DockerImageCode

from cdklabs.generative_ai_cdk_constructs.bedrock import (
    ActionGroupExecutor,
    Agent,
    AgentActionGroup,
    ApiSchema,
    BedrockFoundationModel,
)
from constructs import Construct


class CoffeeOrderStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        powertools_layer = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            id="lambda-powertools",
            layer_version_arn=f"arn:aws:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86_64:5",
        )

        # Define the DynamoDB table
        ecommerce_table = dynamodb.Table(
            self, "GroceryAppTable",
            table_name="GroceryAppTable",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_IMAGE,

        )


        # AppSync API
        api = appsync.GraphqlApi(
            self, "GroceryAgentApi",
            name="grocery-agents-api",
            definition=appsync.Definition.from_schema(
                appsync.SchemaFile.from_asset("graphql/schema.graphql"),

            ),
            log_config=appsync.LogConfig(
                field_log_level=appsync.FieldLogLevel.ALL
            ),


            authorization_config=appsync.AuthorizationConfig(
                default_authorization=appsync.AuthorizationMode(
                    authorization_type=appsync.AuthorizationType.API_KEY
                )
            )
        )

        # Lambda Function for Resolver
        lambda_function = aws_lambda.Function(
            self, "UploadProductsLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="batch_upload_products.handler",
            code=aws_lambda.Code.from_asset("batch_upload")
        )
        # Lambda Function for Resolver
        create_stripe_products_lambda_function = aws_lambda.Function(
            self, "CreateStripeProductsLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="create_stripe_products.handler",
            code=aws_lambda.Code.from_asset("batch_upload")
        )

        # Grant Lambda access to DynamoDB
        ecommerce_table.grant_write_data(lambda_function)
        lambda_function.add_environment("ECOMMERCE_TABLE_NAME", ecommerce_table.table_name)
        # Add Lambda as a DataSource for AppSync
        lambda_ds = api.add_lambda_data_source("LambdaDataSource", lambda_function)

        # Define the Resolver for the uploadProducts Mutation
        lambda_ds.create_resolver(
            id="uploadProductsResolver",
            type_name="Mutation",
            field_name="uploadProducts",
            request_mapping_template=appsync.MappingTemplate.lambda_request(),
            response_mapping_template=appsync.MappingTemplate.lambda_result()
        )
        # Add Lambda as a DataSource for AppSync
        create_stripe_products_lambda_ds = api.add_lambda_data_source("CreateStripeProductsLambdaDataSource", create_stripe_products_lambda_function)

        # Define the Resolver for the uploadProducts Mutation
        create_stripe_products_lambda_ds.create_resolver(
            id="CreateStripeProductsResolver",
            type_name="Mutation",
            field_name="createStripeProducts",
            request_mapping_template=appsync.MappingTemplate.lambda_request(),
            response_mapping_template=appsync.MappingTemplate.lambda_result()
        )



        # Add Global Secondary Indexes (GSIs)
        ecommerce_table.add_global_secondary_index(
            index_name="userOrders",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        ecommerce_table.add_global_secondary_index(
            index_name="orderProducts",
            partition_key=dynamodb.Attribute(
                name="GSI2PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI2SK",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Step 2: Create a Lambda function
        grocery_function = aws_lambda.Function(self, "TriggerStepFunctionsWorkflow",
                                               runtime=aws_lambda.Runtime.PYTHON_3_11,
                                               timeout=Duration.seconds(30),
                                               memory_size=2048,
                                               handler="grocery_list_processor.handler",
                                               code=aws_lambda.Code.from_asset("lambda"))

        grocery_list_bucket = aws_s3.Bucket(self, "grocery-list",
                                            versioned=False,
                                            encryption=aws_s3.BucketEncryption.S3_MANAGED,
                                            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL)

        # Step 3: Grant the Lambda function permissions to read from the S3 bucket
        grocery_list_bucket.grant_read_write(grocery_function)


        # Step 4: Grant the Lambda function permissions to use Textract
        textract_policy = iam.PolicyStatement(
            actions=[
                "textract:DetectDocumentText",
                     "textract:StartDocumentTextDetection",
                     "textract:GetDocumentTextDetection"],
            resources=["*"]  # Grant access to all Textract resources
        )
        grocery_function.add_to_role_policy(textract_policy)
        # Step 5: Add an S3 event trigger to invoke the Lambda function
        notification = aws_s3_notifications.LambdaDestination(grocery_function)
        grocery_list_bucket.add_event_notification(aws_s3.EventType.OBJECT_CREATED, notification)

        # Step 5: Create a Dead-Letter Queue (DLQ) for the SQS queue
        dlq = sqs.Queue(self, "GroceryListDLQ",
                        retention_period=Duration.days(14))  # Retain messages for 14 days

        # Step 6: Create the main SQS queue with a DLQ
        sqs_queue = sqs.Queue(self, "GroceryListTextExtractionQueue",
                              dead_letter_queue=sqs.DeadLetterQueue(
                                  max_receive_count=3,  # Retry 3 times before sending to DLQ
                                  queue=dlq
                              ))

        # Step 7: Grant the first Lambda function permissions to send messages to the SQS queue
        sqs_queue.grant_send_messages(grocery_function)

        # Step 8: Set the SQS queue URL as an environment variable for the Lambda function
        grocery_function.add_environment("SQS_QUEUE_URL", sqs_queue.queue_url)

        # Step 10: Create the second Lambda function (SQS Poller)
        sqs_poller_lambda = aws_lambda.Function(self, "LambdaSQSPoller",
                                                runtime=aws_lambda.Runtime.PYTHON_3_11,
                                                handler="lambda_sqs_poller.handler",
                                                code=aws_lambda.Code.from_asset("lambda"),
                                                timeout=Duration.seconds(30))

        # Step 11: Grant the second Lambda function permissions to poll the SQS queue
        sqs_queue.grant_consume_messages(sqs_poller_lambda)

        sqs_poller_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]  # Grant access to all Bedrock models
        ))

        # Step 11: Add an SQS event source mapping to trigger the Lambda function
        sqs_event_source = lambda_event_sources.SqsEventSource(sqs_queue)
        sqs_poller_lambda.add_event_source(sqs_event_source)

        sqs_poller_lambda.add_environment("SQS_QUEUE_URL", sqs_queue.queue_url)

        # Step 5: (Optional) Output the bucket name and Lambda function ARN
        self.bucket_name = grocery_list_bucket.bucket_name
        self.lambda_arn = grocery_function.function_arn
        self.sqs_queue_url = sqs_queue.queue_url
        self.sqs_poller_lambda_arn = sqs_poller_lambda.function_arn
        self.dlq_url = dlq.queue_url

        action_group_function = aws_lambda.DockerImageFunction(
            self,
            "AgentLambdaFunction",
            architecture=aws_lambda.Architecture.ARM_64,
            function_name="AgentLambdaFunction",
            memory_size=2048,
            timeout=Duration.seconds(30),
            code=DockerImageCode.from_image_asset("lambda"),

        )
        ecommerce_table.grant_full_access(action_group_function)
        action_group_function.add_environment("ECOMMERCE_TABLE_NAME",ecommerce_table.table_name)

        agent = Agent(
            self,
            "Agent",
            foundation_model=BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V1_0,
            instruction="You are a helpful and friendly agent that helps users tell the current time, create stripe "
                        "payment links,batch uploads a list of products into a dynamodb table and schedules meetings",
        )

        executor_group = ActionGroupExecutor(lambda_=action_group_function)

        action_group = AgentActionGroup(
            self,
            "ActionGroup",
            action_group_name="GreatCustomerSupport",
            description="Use these functions for customer support",
            action_group_executor=executor_group,
            action_group_state="ENABLED",
            api_schema=ApiSchema.from_asset("./lambda/openapi.json"),
        )
        agent.add_action_group(action_group)
        # Output the AppSync GraphQL Endpoint
        CfnOutput(
            self, "GraphQLEndpoint",
            value=api.graphql_url
        )
        CfnOutput(
            self, "GraphQLApiKey",
            value=api.api_key
        )


