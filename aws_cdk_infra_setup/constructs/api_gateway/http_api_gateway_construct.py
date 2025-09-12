import os
import json
from aws_cdk import (
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_lambda as _lambda
)
from constructs import Construct


class HttpApiGatewayConstruct(Construct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            iam_roles_construct=None,  # optional
            *,
            api_config_file=None,
            http_api_configs=None,  # NEW: allow direct config dict
            lambda_map=None,  # NEW: accept but optional
            project_root=None,
            **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        self.iam_roles_construct = iam_roles_construct
        self.lambda_map = lambda_map or {}
        self.project_root = project_root or os.getcwd()

        # Load API config
        if api_config_file:
            api_config_path = os.path.join(self.project_root, api_config_file)
            if not os.path.exists(api_config_path):
                raise FileNotFoundError(f"API config file not found: {api_config_path}")
            with open(api_config_path, "r") as f:
                self.api_config = json.load(f)
        elif http_api_configs:
            self.api_config = http_api_configs
        else:
            raise ValueError("Either api_config_file or http_api_configs is required")

        # Create HTTP API
        self.http_api = apigwv2.CfnApi(
            self,
            f"{self.api_config['name']}-api",
            name=self.api_config["name"],
            protocol_type="HTTP",
            cors_configuration=self.api_config.get("cors")
        )

        # Create stage (required for HTTP API)
        self.stage = apigwv2.CfnStage(
            self,
            f"{self.api_config['name']}-stage",
            api_id=self.http_api.ref,
            stage_name="$default",
            auto_deploy=True
        )

        # Create authorizers first
        self.authorizers = {}
        self._create_authorizers()

        # Create integrations & routes
        self._setup_routes()

    def _create_authorizers(self):
        """Create all authorizers defined in the config"""
        authorizers_config = self.api_config.get("authorizers", {})

        for auth_name, auth_config in authorizers_config.items():
            try:
                func_name = auth_config["function_name"]

                # Get Lambda function from lambda_map
                if func_name not in self.lambda_map:
                    print(f"⚠️ Lambda function '{func_name}' not found in lambda_map for authorizer '{auth_name}'")
                    continue

                lambda_fn = self.lambda_map[func_name]

                authorizer = apigwv2.CfnAuthorizer(
                    self,
                    f"{auth_name.replace('_', '-').replace(' ', '-')}-authorizer",
                    api_id=self.http_api.ref,
                    authorizer_type="REQUEST",
                    authorizer_uri=f"arn:aws:apigateway:{Stack.of(self).region}:lambda:path/2015-03-31/functions/{lambda_fn.function_arn}/invocations",
                    identity_source=[auth_config.get("identity_source", "$request.header.Authorization")],
                    authorizer_result_ttl_in_seconds=auth_config.get("ttl_seconds", 300),
                    name=f"{auth_name}-auth",
                    authorizer_payload_format_version="2.0",
                )

                self.authorizers[auth_name] = authorizer.ref
                print(f"✅ Created authorizer: {auth_name}")

            except Exception as e:
                print(f"⚠️ Failed to create authorizer '{auth_name}': {str(e)}")

    def _setup_routes(self):
        """Setup routes based on the configuration structure"""
        routes_config = self.api_config.get("routes", {})

        for route_name, route_config in routes_config.items():
            try:
                resource_path = route_config.get("resource_path", f"/{route_name}")
                methods = route_config.get("methods", ["GET"])
                authorizations = route_config.get("authorization", {})

                # Determine integration type and target
                integration_target = self._determine_integration_target(route_name, route_config)

                if not integration_target:
                    print(f"⚠️ No valid integration target found for route '{route_name}', skipping")
                    continue

                # Create integration
                integration = self._create_integration(route_name, integration_target)

                # Create routes for each method
                for method in methods:
                    method_upper = method.upper()

                    # Determine authorizer for this method
                    auth_name = authorizations.get(method_upper)
                    authorizer_id = self.authorizers.get(auth_name) if auth_name else None

                    route_key = f"{method_upper} {resource_path}"

                    apigwv2.CfnRoute(
                        self,
                        f"{route_name}-{method_upper.lower()}-route",
                        api_id=self.http_api.ref,
                        route_key=route_key,
                        target=f"integrations/{integration.ref}",
                        authorizer_id=authorizer_id,
                        authorization_type="CUSTOM" if authorizer_id else "NONE"
                    )

                    auth_info = f" with auth '{auth_name}'" if auth_name else " (no auth)"
                    print(f"✅ Created route: {route_key}{auth_info}")

            except Exception as e:
                print(f"⚠️ Failed to create route '{route_name}': {str(e)}")

    def _determine_integration_target(self, route_name, route_config):
        """Determine what this route should integrate with"""

        # Option 1: Check if there's a Lambda function with the same name as the route
        if route_name in self.lambda_map:
            return {"type": "lambda", "target": self.lambda_map[route_name]}

        # Option 2: Check for explicit function_name in route config
        func_name = route_config.get("function_name")
        if func_name and func_name in self.lambda_map:
            return {"type": "lambda", "target": self.lambda_map[func_name]}

        # Option 3: Check for lambda config in route
        lambda_config = route_config.get("lambda")
        if lambda_config:
            if isinstance(lambda_config, str):
                # Lambda is just a function name
                if lambda_config in self.lambda_map:
                    return {"type": "lambda", "target": self.lambda_map[lambda_config]}
            elif isinstance(lambda_config, dict):
                func_name = lambda_config.get("function_name")
                if func_name and func_name in self.lambda_map:
                    return {"type": "lambda", "target": self.lambda_map[func_name]}

        # Option 4: Use global HTTP endpoint if specified
        if self.api_config.get("integration_target") == "HTTP URI" and self.api_config.get("url"):
            return {"type": "http", "target": self.api_config["url"]}

        # Option 5: Check for route-specific HTTP endpoint
        if route_config.get("url"):
            return {"type": "http", "target": route_config["url"]}

        print(f"⚠️ No integration target found for route '{route_name}'")
        print(f"   Available Lambda functions: {list(self.lambda_map.keys())}")
        return None

    def _create_integration(self, route_name, integration_target):
        """Create the appropriate integration based on target type"""

        if integration_target["type"] == "lambda":
            lambda_fn = integration_target["target"]
            return apigwv2.CfnIntegration(
                self,
                f"{route_name}-lambda-integration",
                api_id=self.http_api.ref,
                integration_type="AWS_PROXY",
                integration_uri=f"arn:aws:apigateway:{Stack.of(self).region}:lambda:path/2015-03-31/functions/{lambda_fn.function_arn}/invocations",
                payload_format_version="2.0",
                integration_method="POST",
            )

        elif integration_target["type"] == "http":
            http_url = integration_target["target"]
            return apigwv2.CfnIntegration(
                self,
                f"{route_name}-http-integration",
                api_id=self.http_api.ref,
                integration_type="HTTP_PROXY",
                integration_uri=http_url,
                integration_method=self.api_config.get("http_method", "GET"),
                payload_format_version="1.0",  # Required for HTTP proxy integrations
            )

        else:
            raise ValueError(f"Unknown integration type: {integration_target['type']}")

    def _get_or_create_lambda(self, route_cfg):
        """
        Legacy method - kept for backwards compatibility
        """
        print("⚠️ _get_or_create_lambda called - this shouldn't happen with the new structure")
        return None

    def _create_lambda(self, route_cfg):
        """
        Legacy method - kept for backwards compatibility
        """
        print("⚠️ _create_lambda called - this shouldn't happen with the new structure")
        return None

    def _create_authorizer(self, auth_cfg):
        """
        Legacy method - kept for backwards compatibility
        """
        print("⚠️ _create_authorizer called - this shouldn't happen with the new structure")
        return None