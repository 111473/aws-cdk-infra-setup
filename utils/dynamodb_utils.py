import os
import json
import boto3


# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')


# ---------- Utility Functions ----------

def get_dynamodb_table(table_name):
    """Get DynamoDB table resource"""
    return dynamodb.Table(table_name)


def create_response(status_code, body):
    """
    Create a standard Lambda HTTP response.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


