import json
import os
import boto3

from botocore.exceptions import ClientError
from utils.dynamodb_utils import create_response

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")


def create_coffee(event, context):
    """
    Lambda function to create a new coffee item in DynamoDB.
    - Requires coffeeId, name, price, and available.
    - Uses a condition to prevent overwriting existing items.
    """
    table_name = os.getenv("tableName", "CoffeeShop")
    table = dynamodb.Table(table_name)

    # Parse request body
    body = event.get("body")
    try:
        body_data = json.loads(body or "{}")
    except json.JSONDecodeError:
        return create_response(400, {"error": "Invalid JSON in request body"})

    coffee_id = body_data.get("coffeeId")
    name = body_data.get("name")
    price = body_data.get("price")
    available = body_data.get("available")

    print("values:", coffee_id, name, price, available)

    # Validate required fields
    if not coffee_id or not name or not price or available is None:
        return create_response(
            409,
            {
                "error": "Missing required attributes: coffeeId, name, price, or available."
            },
        )

    try:
        # Equivalent of PutCommand with ConditionExpression
        response = table.put_item(
            Item={
                "coffeeId": coffee_id,
                "name": name,
                "price": price,
                "available": available,
            },
            ConditionExpression="attribute_not_exists(coffeeId)",
        )

        return create_response(201, {"message": "Item Created Successfully!", "response": response})

    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return create_response(409, {"error": "Item already exists!"})
        else:
            print("Error inserting data into DynamoDB:", err)
            return create_response(
                500,
                {
                    "error": "Internal Server Error!",
                    "message": str(err),
                },
            )