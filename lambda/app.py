
import os
from time import time

import boto3
import stripe
from pydantic import EmailStr, ValidationError, BaseModel, HttpUrl
from typing_extensions import Annotated
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import BedrockAgentResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.openapi.params import Body, Query

tracer = Tracer()
logger = Logger()
app = BedrockAgentResolver()
dynamodb = boto3.resource("dynamodb")

table_name = os.environ.get("ECOMMERCE_TABLE_NAME")

table = dynamodb.Table(table_name)
# Set your Stripe API key
stripe.api_key = 'sk_test_o5XBQtVklHa7okPAhm5Ey61C00T7DHjBgB'

from datetime import datetime
from typing import List


class Package(BaseModel):
    height: int
    length: int
    weight: int
    width: int


class Product(BaseModel):
    productId: str
    category: str
    createdDate: datetime
    description: str
    modifiedDate: datetime
    name: str
    package: Package
    pictures: List[HttpUrl]
    price: int
    tags: List[str]


'''
@app.get("/schedule_meeting", description="Schedules a meeting with the team")
@tracer.capture_method
def schedule_meeting(
        email: Annotated[EmailStr, Query(description="The email address of the customer")],
) -> Annotated[bool, Body(description="Whether the meeting was scheduled successfully")]:
    logger.info("Scheduling a meeting", email=email)
    return True
'''


@app.post("/list_of_items", description="receives a json array made up of json objects, maps each object to "
                                        "a pydantic model called Product and returns the json array")
@tracer.capture_method
def list_of_items(list_items: Annotated[
    list, Query(examples=[{
        "PK": "PRODUCT",
        "SK": "PRODUCT#4c1fadaa-213a-4ea8-aa32-58c217604e3c",
        "productId": "4c1fadaa-213a-4ea8-aa32-58c217604e3c",
        "category": "fruit",
        "createdDate": "2017-04-17T01:14:03 -02:00",
        "description": "Culpa non veniam deserunt dolor irure elit cupidatat culpa consequat nulla irure aliqua.",
        "modifiedDate": "2019-03-13T12:18:27 -01:00",
        "name": "Fresh Lemons",
        "package": {
            "height": 948,
            "length": 455,
            "weight": 54,
            "width": 905
        },
        "pictures": [
            "https://img.freepik.com/free-photo/lemon_1205-1667.jpg?w=1480&t=st=1689112951~exp=1689113551~hmac=196483001817bd24a3d1eeb35a23ddf9911ac5628fe6df0758a47faa7ed3e332"
        ],
        "price": 7160,
        "tags": [
            "mollit",
            "ad",
            "eiusmod",
            "irure",
            "tempor"
        ]
    }
    ], description="A list of items")]) -> Annotated[
    list, Body(description="returns list of items")]:
    logger.info(f"list of items {list_items}")

    return list_items


@app.post("/populate_db", description="Populates the database with a list of json objects gotten from a json array")
@tracer.capture_method
def add_products_db(list_items: Annotated[
    list, Query(examples=[{
        "PK": "PRODUCT",
        "SK": "PRODUCT#4c1fadaa-213a-4ea8-aa32-58c217604e3c",
        "productId": "4c1fadaa-213a-4ea8-aa32-58c217604e3c",
        "category": "fruit",
        "createdDate": "2017-04-17T01:14:03 -02:00",
        "description": "Culpa non veniam deserunt dolor irure elit cupidatat culpa consequat nulla irure aliqua.",
        "modifiedDate": "2019-03-13T12:18:27 -01:00",
        "name": "Fresh Lemons",
        "package": {
            "height": 948,
            "length": 455,
            "weight": 54,
            "width": 905
        },
        "pictures": [
            "https://img.freepik.com/free-photo/lemon_1205-1667.jpg?w=1480&t=st=1689112951~exp=1689113551~hmac=196483001817bd24a3d1eeb35a23ddf9911ac5628fe6df0758a47faa7ed3e332"
        ],
        "price": 7160,
        "tags": [
            "mollit",
            "ad",
            "eiusmod",
            "irure",
            "tempor"
        ]
    }
    ], description="The list items")]) -> Annotated[
    bool, Body(description="Whether the products were added to the successfully")]:
    """
       Batch loads a list of products into DynamoDB.


       Returns:
           dict: A response indicating the status of the operation.
       """

    logger.append_keys(
        session_id=app.current_event.session_id,
        action_group=app.current_event.action_group,
        input_text=app.current_event.input_text,

    )
    try:

        logger.info(f"list of items {list_items}")

        # Validate the input using Pydantic
        product_list: List[Product] = [Product(**item) for item in list_items]

    except ValidationError as e:
        logger.exception("An unexpected error occurred", log=e)
        return False

    # Batch load products into DynamoDB
    with table.batch_writer() as batch:
        for product in product_list:
            batch.put_item(
                Item={
                    "PK": "PRODUCT",
                    "SK": f"PRODUCT#{product.productId}",
                    "productId": product.productId,
                    "category": product.category,
                    "createdDate": product.createdDate,
                    "description": product.description,
                    "modifiedDate": product.modifiedDate,
                    "name": product.name,
                    "package": product.package,
                    "pictures": product.pictures,
                    "price": product.price,
                    "tags": product.tags,
                }
            )

    logger.info("Products uploaded successfully")
    return True


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


if __name__ == "__main__":
    print(app.get_openapi_json_schema())
