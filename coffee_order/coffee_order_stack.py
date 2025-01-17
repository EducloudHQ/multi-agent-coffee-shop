from aws_cdk import (
    Stack, Aws, Duration,
)

from aws_cdk import aws_lambda
from aws_cdk.aws_lambda import DockerImageCode
from aws_cdk.aws_lambda_python_alpha import PythonFunction, BundlingOptions
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

        action_group_function = aws_lambda.DockerImageFunction(
            self,
            "AgentLambdaFunction",
            architecture=aws_lambda.Architecture.ARM_64,


            function_name="AgentLambdaFunction",
            memory_size=2048,
            timeout=Duration.seconds(30),
            code=DockerImageCode.from_image_asset("lambda"),

        )

        agent = Agent(
            self,
            "Agent",
            foundation_model=BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V1_0,
            instruction="You are a helpful and friendly agent that answers questions about insurance claims.",
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
