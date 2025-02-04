import json
import os
import stripe
import boto3

stripe.api_key = 'sk_test_o5XBQtVklHa7okPAhm5Ey61C00T7DHjBgB'

with open("product_list.json", "r") as product_list:
    product_list = json.load(product_list)


def handler(event, context):
    print("Retrieving all products: %s", product_list)
    print(f"item id is {product_list[0]['productId']}")
    response = ''
    # Iterate through the list and create products and prices
    for product_data in product_list:
        try:
            # Create a product
            product = stripe.Product.create(
                name=product_data["name"],
                description=product_data["description"],
                metadata={
                    "category": product_data["category"],
                    "createdDate": product_data["createdDate"],
                    "modifiedDate": product_data["modifiedDate"],
                    "productId": product_data["productId"],
                    "tags": ", ".join(product_data["tags"]),
                    "package": json.dumps(product_data["package"]),
                },
                images=product_data["pictures"],
            )
            print(f"Product created: {product.name} (ID: {product.id})")

            # Create a price for the product
            price = stripe.Price.create(
                unit_amount=product_data["price"],  # Price in cents
                currency="usd",  # Currency code
                product=product.id,  # Link to the product
            )
            print(f"Price created: {price.unit_amount / 100} {price.currency} (ID: {price.id})")
            response = "Product Created"


        except stripe.error.StripeError as e:
            print(f"Error creating product or price for {product_data['name']}: {e.user_message}")
            response = "Failed to create Product"

    return response
