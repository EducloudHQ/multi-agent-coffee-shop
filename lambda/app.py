from time import time

from pydantic import EmailStr
from typing_extensions import Annotated

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import BedrockAgentResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.openapi.params import Body, Query

tracer = Tracer()
logger = Logger()
app = BedrockAgentResolver()


@app.get("/schedule_meeting", description="Schedules a meeting with the team")
@tracer.capture_method
def schedule_meeting(
        email: Annotated[EmailStr, Query(description="The email address of the customer")],
) -> Annotated[bool, Body(description="Whether the meeting was scheduled successfully")]:
    logger.info("Scheduling a meeting", email=email)
    return True

@app.get("/current_time", description="Gets the current time in seconds")
@tracer.capture_method
def current_time() -> int:
    return int(time())


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)

'''
if __name__ == "__main__":
    print(app.get_openapi_json_schema())
'''

