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

        # if not rest_api_configs:
        #     print("⚠️ No REST API configuration provided, skipping API creation.")
        #     return
        #
        # api_name = rest_api_configs.get("name", "product-rest-api")
        # resources_cfg = rest_api_configs.get("resources", {})
        # api_description = rest_api_configs.get("description") or "CDK Generated API"
        #
        # rest_api = apigw.RestApi(
        #     self,
        #     "resourcesRestApi",
        #     rest_api_name=api_name,
        #     description=api_description,
        #     endpoint_configuration=apigw.EndpointConfiguration(types=[apigw.EndpointType.REGIONAL]),
        #     deploy=True,
        #     deploy_options=apigw.StageOptions(stage_name=rest_api_configs.get("stage_name", "dev")),
        # )
        #
        # # 4️⃣ Create Authorizers
        # authorizers_cfg = rest_api_configs.get("authorizers", {})
        # authorizer_map: Dict[str, apigw.IAuthorizer] = {}
        #
        # for auth_name, auth_cfg in authorizers_cfg.items():
        #     lambda_fn_name = auth_cfg.get("function_name")
        #     lambda_fn = lambda_map.get(lambda_fn_name)
        #     print("AUTH_NAME >>>>>>>>>>>", auth_name)
        #     if not lambda_fn:
        #         print(f"⚠️ Authorizer Lambda '{lambda_fn_name}' not found for '{auth_name}', skipping authorizer.")
        #         continue
        #
        #     auth_type = auth_cfg.get("type", "TOKEN").upper()
        #     identity_source = auth_cfg.get("identity_source", "method.request.header.Authorization")
        #
        #     try:
        #         if auth_type == "TOKEN":
        #             # TokenAuthorizer expects a single string, not a list
        #             if isinstance(identity_source, list):
        #                 identity_source = identity_source[0]
        #             authorizer = apigw.TokenAuthorizer(
        #                 self,
        #                 f"{auth_name.replace('-', '')}TokenAuthorizer",  # 🔧 FIX: Clean construct ID
        #                 handler=lambda_fn,
        #                 identity_source=identity_source,
        #             )
        #         elif auth_type == "REQUEST":
        #             # RequestAuthorizer expects a list of IdentitySource objects
        #             if isinstance(identity_source, str):
        #                 identity_source = [identity_source]
        #
        #             # 🔧 FIX: Convert strings to IdentitySource objects
        #             identity_sources = []
        #             for source in identity_source:
        #                 if "header" in source:
        #                     header_name = source.split(".")[-1]  # Extract header name
        #                     identity_sources.append(apigw.IdentitySource.header(header_name))
        #                 elif "querystring" in source:
        #                     query_param = source.split(".")[-1]  # Extract query parameter name
        #                     identity_sources.append(apigw.IdentitySource.query_string(query_param))
        #                 else:
        #                     # Default to header if format is unclear
        #                     identity_sources.append(apigw.IdentitySource.header("Authorization"))
        #
        #             authorizer = apigw.RequestAuthorizer(
        #                 self,
        #                 f"{auth_name.replace('-', '')}RequestAuthorizer",  # 🔧 FIX: Clean construct ID
        #                 handler=lambda_fn,
        #                 identity_sources=identity_sources,
        #             )
        #         else:
        #             print(f"⚠️ Unknown authorizer type '{auth_type}' for {auth_name}, skipping.")
        #             continue
        #
        #         authorizer_map[auth_name] = authorizer
        #         print(f"✅ Created {auth_type} authorizer: {auth_name}")
        #
        #     except Exception as e:
        #         print(f"⚠️ Failed to create authorizer '{auth_name}': {str(e)}")
        #         continue
        #
        # print("🔹 Authorizers created:", list(authorizer_map.keys()))
        #
        # # 5️⃣ Create Resources and Methods
        # created_resources = {}  # Track created resources to avoid duplicates
        #
        # for resource_name, cfg in resources_cfg.items():
        #     try:
        #         # 🔧 FIX: Handle nested resource paths properly
        #         path_parts = cfg.get("resource_path", f"/{resource_name}").strip("/").split("/")
        #         parent_resource = rest_api.root
        #
        #         # Build the full path
        #         current_path = ""
        #         for part in path_parts:
        #             if not part:  # Skip empty parts
        #                 continue
        #
        #             current_path = f"{current_path}/{part}" if current_path else part
        #
        #             # Check if resource already exists
        #             if current_path in created_resources:
        #                 parent_resource = created_resources[current_path]
        #             else:
        #                 # Try to find existing resource
        #                 existing_resource = None
        #                 for child in parent_resource.node.children:
        #                     if hasattr(child, 'path_part') and child.path_part == part:
        #                         existing_resource = child
        #                         break
        #
        #                 if existing_resource:
        #                     parent_resource = existing_resource
        #                 else:
        #                     parent_resource = parent_resource.add_resource(part)
        #
        #                 created_resources[current_path] = parent_resource
        #
        #         resource = parent_resource
        #
        #         # Handle CORS
        #         if cfg.get("cors_enabled", False):
        #             resource.add_cors_preflight(
        #                 allow_origins=apigw.Cors.ALL_ORIGINS,
        #                 allow_methods=apigw.Cors.ALL_METHODS,
        #                 allow_headers=[
        #                     "Content-Type",
        #                     "X-Amz-Date",
        #                     "Authorization",
        #                     "X-Api-Key",
        #                     "X-Amz-Security-Token",
        #                     "authorizationToken",  # 🔧 FIX: Add custom headers
        #                 ],
        #             )
        #
        #         # Get Lambda function
        #         lambda_fn_name = cfg.get("function_name")
        #         lambda_fn = lambda_map.get(lambda_fn_name)
        #         if not lambda_fn:
        #             print(f"⚠️ Lambda '{lambda_fn_name}' not found for resource '{resource_name}', skipping methods.")
        #             continue
        #
        #         # 🔧 FIX: Create Lambda integration with proper error handling
        #         lambda_integration = apigw.LambdaIntegration(
        #             lambda_fn,
        #             proxy=True,  # Enable Lambda proxy integration
        #             allow_test_invoke=True,
        #         )
        #
        #         methods = cfg.get("methods", [])
        #         authorizations = cfg.get("authorization", {})
        #
        #         for method in methods:
        #             method_upper = method.upper()
        #             if method_upper == "OPTIONS":
        #                 continue  # Already handled by CORS preflight
        #
        #             # Resolve authorizer
        #             auth_name = authorizations.get(method_upper)
        #             authorizer = None
        #             auth_type = None
        #
        #             if auth_name:
        #                 authorizer = authorizer_map.get(auth_name)
        #                 if authorizer:
        #                     auth_type = apigw.AuthorizationType.CUSTOM
        #                     print(f"✅ Using authorizer '{auth_name}' for {method_upper} {resource_name}")
        #                 else:
        #                     print(
        #                         f"⚠️ Authorizer '{auth_name}' not found for method '{method_upper}' on '{resource_name}'")
        #                     auth_type = apigw.AuthorizationType.NONE
        #             else:
        #                 auth_type = apigw.AuthorizationType.NONE
        #
        #             # Add method
        #             try:
        #                 resource.add_method(
        #                     method_upper,
        #                     lambda_integration,
        #                     api_key_required=method_upper in cfg.get("require_api_key", []),
        #                     authorization_type=auth_type,
        #                     authorizer=authorizer,
        #                 )
        #                 print(f"✅ Added {method_upper} method to {resource_name}")
        #
        #             except Exception as e:
        #                 print(f"⚠️ Failed to add {method_upper} method to {resource_name}: {str(e)}")
        #
        #     except Exception as e:
        #         print(f"⚠️ Failed to create resource '{resource_name}': {str(e)}")
        #         continue
        #
        # # 6️⃣ Create Usage Plan
        # usage_cfg = rest_api_configs.get("usage_plan", {})
        # if usage_cfg:
        #     try:
        #         plan = apigw.UsagePlan(
        #             self,
        #             "usage_planRestApi",
        #             name=f"{api_name}-usage-plan",
        #             throttle=apigw.ThrottleSettings(
        #                 rate_limit=usage_cfg.get("rate_limit", 100),
        #                 burst_limit=usage_cfg.get("burst_limit", 20),
        #             ),
        #             quota=apigw.QuotaSettings(
        #                 limit=usage_cfg.get("limit", 1000),
        #                 period=apigw.Period[usage_cfg.get("period", "MONTH").upper()],
        #             ),
        #         )
        #         plan.add_api_stage(stage=rest_api.deployment_stage)
        #         print("✅ Usage plan created successfully")
        #
        #     except Exception as e:
        #         print(f"⚠️ Failed to create usage plan: {str(e)}")
        #
        # print(f"✅ REST API '{api_name}' created with resources: {list(resources_cfg.keys())}")

