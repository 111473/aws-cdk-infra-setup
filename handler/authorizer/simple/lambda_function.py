import json
import boto3

ssm = boto3.client('ssm', region_name="ap-south-1")


def lambda_handler(event, context):
    parameter_name = '/myapp/access-token'

    token = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
    tokenFromHeader = event['headers']['authorization']

    if tokenFromHeader == token['Parameter']['Value']:
        auth_status = True
    else:
        auth_status = False

    authResponse = {
        'isAuthorized': auth_status
    }

    return authResponse