import json
import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm', region_name="us-east-1")


def lambda_handler(event, context):
    logger.info("Incoming event: %s", json.dumps(event))

    parameter_name = '/myapp/access-token'

    try:
        token_from_ssm = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        expected_token = token_from_ssm['Parameter']['Value']
    except Exception as e:
        logger.error("Failed to retrieve token from SSM: %s", str(e))
        raise Exception("Unauthorized")

    # Extract token from header
    token_from_header = event.get('authorizationToken')
    if not token_from_header:
        logger.warning("Missing authorizationToken in event")
        raise Exception("Unauthorized")

    # Comparison (simple string match — could be more secure in real scenarios)
    if token_from_header == expected_token:
        effect = 'Allow'
    else:
        logger.warning("Token mismatch: provided '%s'", token_from_header)
        effect = 'Deny'

    policy = generate_policy(principal_id="user", effect=effect, resource=event.get("methodArn", "*"))
    logger.info("Authorization result: %s", effect)
    return policy


def generate_policy(principal_id, effect, resource):
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
