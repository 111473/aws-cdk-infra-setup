from typing import Dict
from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
)
from constructs import Construct

from aws_cdk_infra_setup.constructs.api_gateway.http_api_gateway_construct import HttpApiGatewayConstruct
from aws_cdk_infra_setup.constructs.iam_roles_construct import IamRoleConstruct
from aws_cdk_infra_setup.constructs.lambda_functions_construct import LambdaFunctionConstruct
from aws_cdk_infra_setup.constructs.api_gateway.rest_api_gateway_construct import RestApiGatewayConstruct


class AwsCdkInfraSetupStack(Stack):
    def __init__(
            self,
            scope: Construct,
            id: str,
            *,
            iam_role_configs=None,
            lambda_function_configs=None,
            rest_api_configs=None,
            http_api_configs=None,
            project_root=None,
            **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        # 1️⃣ Create IAM Roles
        iam_roles_construct = IamRoleConstruct(
            self,
            "IamRoles",
            iam_role_configs=iam_role_configs or [],
        )

        # 2️⃣ Create Lambda Functions
        lambda_construct = LambdaFunctionConstruct(
            self,
            "LambdaFunctions",
            iam_roles_construct=iam_roles_construct,
            lambda_functions_config_files=lambda_function_configs or [],
            project_root=project_root,
        )

        # 🔧 FIX: Build Lambda lookup dict from the construct's stored functions
        lambda_map: Dict[str, _lambda.IFunction] = lambda_construct.lambda_functions.copy()

        print("🔹 Lambda functions created:", list(lambda_map.keys()))

        # 3️⃣ Create REST APIs (support multiple configs)
        for idx, api_cfg in enumerate(rest_api_configs):
            api_name = api_cfg.get("name", f"rest-api-{idx}")

            RestApiGatewayConstruct(
                self,
                f"RestApi{idx}_{api_name.replace('-', '')}",
                lambda_map=lambda_map,
                rest_api_configs=api_cfg
            )

        print("✅ All REST APIs created successfully")

        # 4️⃣ Create HTTP APIs (support multiple configs)
        for idx, api_cfg in enumerate(http_api_configs):
            api_name = api_cfg.get("name", f"http-api-{idx}")

            HttpApiGatewayConstruct(
                self,
                f"HttpApi{idx}_{api_name.replace('-', '')}",
                iam_roles_construct=iam_roles_construct,
                lambda_map=lambda_map,
                http_api_configs=api_cfg
            )

        print("✅ All HTTP APIs created successfully")


