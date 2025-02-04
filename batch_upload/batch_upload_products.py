import json
import os

import boto3

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get("ECOMMERCE_TABLE_NAME")
table = dynamodb.Table(table_name)

with open("product_list.json", "r") as product_list:
    product_list = json.load(product_list)

def handler(event, context):
    print("Retrieving all products: %s", product_list)
    print(f"item id is {product_list[0]['productId']}")

    try:
        with table.batch_writer() as batch:
            for item in product_list:
                batch.put_item(
                    Item={
                        "PK": f"PRODUCT",
                        "SK": f"PRODUCT#{item['productId']}",
                        "productId": item["productId"],
                        "category": item["category"],
                        "createdDate": item["createdDate"],
                        "description": item["description"],
                        "modifiedDate": item["modifiedDate"],
                        "name": item["name"],
                        "package": item["package"],
                        "pictures": item["pictures"],
                        "price": item["price"],
                        "tags": item["tags"],
                    }
                )
        return True
    except Exception as e:
        print(f"Exception: {e}")
        return False











