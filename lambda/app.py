import os
from time import time
import stripe
from pydantic import EmailStr
from typing_extensions import Annotated
from stripe_agent_toolkit.langchain.toolkit import StripeAgentToolkit
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import BedrockAgentResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.openapi.params import Body, Query

tracer = Tracer()
logger = Logger()
app = BedrockAgentResolver()

# Set your Stripe API key
stripe.api_key = 'sk_test_o5XBQtVklHa7okPAhm5Ey61C00T7DHjBgB'

'''
@app.get("/schedule_meeting", description="Schedules a meeting with the team")
@tracer.capture_method
def schedule_meeting(
        email: Annotated[EmailStr, Query(description="The email address of the customer")],
) -> Annotated[bool, Body(description="Whether the meeting was scheduled successfully")]:
    logger.info("Scheduling a meeting", email=email)
    return True
'''


@app.get("/payment_link", description="Creates a stripe payment link")
@tracer.capture_method
def payment_link(
        product_name: Annotated[str, Query(description="The Product name")],
        qty: Annotated[int, Query(description="The Product quantity")],
) -> str:
    logger.info("product name", product_name=product_name)
    logger.info("product qty", qty=qty)

    try:
        # Step 1: Retrieve the product by name
        products = stripe.Product.list(limit=100)  # Adjust limit as needed
        product = None

        # Filter products by name
        for p in products.auto_paging_iter():
            if p.name == product_name:
                product = p
                break

        if not product:
            logger.error(f"No product found with name: {product_name}")
            return f"No product found with name: {product_name}"

        logger.info(f"Product found! ID: {product.id}")

        # Step 2: Retrieve the price for the product
        prices = stripe.Price.list(product=product.id, limit=1)  # Get the first price
        if not prices.data:
            logger.error(f"No price found for product ID: {product.id}")
            return f"No price found for product ID: {product.id}"

        price = prices.data[0]  # Get the first price in the list
        logger.debug(f"Price found! ID: {price.id}, Amount: {price.unit_amount / 100} {price.currency.upper()}")

        # Step 3: Create a payment link using the Price ID
        payment_link = stripe.PaymentLink.create(
            line_items=[
                {
                    'price': price.id,
                    'quantity': qty,
                },
            ],
        )
        logger.info(f"Payment Link URL: {payment_link.url}")
        return f"Payment Link URL: {payment_link}"



    except stripe.error.StripeError as e:
        logger.error(f"Error: {e.user_message}")


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
