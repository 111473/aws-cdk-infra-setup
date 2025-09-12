import os
import boto3

from botocore.exceptions import ClientError
from utils.dynamodb_utils import create_response


# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")


def get_coffee(event, context):
    """
    Lambda function to get coffee item(s) from DynamoDB.
    - If an id is provided in pathParameters, fetch single item (GetItem).
    - Otherwise, scan the whole table.
    """
    table_name = os.getenv("tableName", "CoffeeShop")
    table = dynamodb.Table(table_name)

    path_params = event.get("pathParameters") or {}
    coffee_id = path_params.get("id")

    try:
        if coffee_id:
            # Equivalent of GetCommand
            response = table.get_item(
                Key={"coffeeId": coffee_id}
            )
        else:
            # Equivalent of ScanCommand
            response = table.scan()

        return create_response(200, response)

    except ClientError as err:
        print("Error fetching data from DynamoDB:", err)
        return create_response(500, {"error": str(err)})
