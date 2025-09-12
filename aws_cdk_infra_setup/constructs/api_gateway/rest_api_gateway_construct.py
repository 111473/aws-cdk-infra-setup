from typing import Dict, Optional, Union, List
from aws_cdk import (
    aws_apigateway as apigw,
    aws_lambda as _lambda,
)
from constructs import Construct


class RestApiGatewayConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        lambda_map: Dict[str, _lambda.IFunction],
        rest_api_configs: Optional[Union[dict, List[dict]]] = None,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        # Normalize input: single dict -> list
        if not rest_api_configs:
            print("⚠️ No REST API configuration provided, skipping API creation.")
            self.rest_apis = []
            self.authorizer_maps = []
            return
        if isinstance(rest_api_configs, dict):
            rest_api_configs = [rest_api_configs]

        self.rest_apis = []
        self.authorizer_maps = []

        for idx, api_cfg in enumerate(rest_api_configs):
            api_name = api_cfg.get("name", f"rest-api-{idx}")
            resources_cfg = api_cfg.get("resources", {})
            api_description = api_cfg.get("description") or "CDK Generated API"
            stage_name = api_cfg.get("stage_name", "dev")

            rest_api = apigw.RestApi(
                self,
                f"resourcesRestApi{idx}_{api_name.replace('-', '')}",
                rest_api_name=api_name,
                description=api_description,
                endpoint_configuration=apigw.EndpointConfiguration(types=[apigw.EndpointType.REGIONAL]),
                deploy=True,
                deploy_options=apigw.StageOptions(stage_name=stage_name),
            )
            self.rest_apis.append(rest_api)

            # ----------------- Create Authorizers ----------------- #
            authorizer_map: Dict[str, apigw.IAuthorizer] = {}
            authorizers_cfg = api_cfg.get("authorizers", {})

            for auth_name, auth_cfg in authorizers_cfg.items():
                lambda_fn_name = auth_cfg.get("function_name")
                lambda_fn = lambda_map.get(lambda_fn_name)
                if not lambda_fn:
                    print(f"⚠️ Authorizer Lambda '{lambda_fn_name}' not found for '{auth_name}', skipping.")
                    continue

                auth_type = auth_cfg.get("type", "TOKEN").upper()
                identity_source = auth_cfg.get("identity_source", "method.request.header.Authorization")

                if auth_type == "TOKEN":
                    if isinstance(identity_source, list):
                        identity_source = identity_source[0]
                    authorizer = apigw.TokenAuthorizer(
                        self,
                        f"{auth_name.replace('-', '')}TokenAuthorizer{idx}",
                        handler=lambda_fn,
                        identity_source=identity_source,
                    )
                elif auth_type == "REQUEST":
                    if isinstance(identity_source, str):
                        identity_source = [identity_source]
                    identity_sources = []
                    for source in identity_source:
                        if "header" in source:
                            identity_sources.append(apigw.IdentitySource.header(source.split(".")[-1]))
                        elif "querystring" in source:
                            identity_sources.append(apigw.IdentitySource.query_string(source.split(".")[-1]))
                        else:
                            identity_sources.append(apigw.IdentitySource.header("Authorization"))
                    authorizer = apigw.RequestAuthorizer(
                        self,
                        f"{auth_name.replace('-', '')}RequestAuthorizer{idx}",
                        handler=lambda_fn,
                        identity_sources=identity_sources,
                    )
                else:
                    print(f"⚠️ Unknown authorizer type '{auth_type}' for {auth_name}, skipping.")
                    continue

                authorizer_map[auth_name] = authorizer

            self.authorizer_maps.append(authorizer_map)

            # ----------------- Create Resources & Methods ----------------- #
            self._create_resources_and_methods(rest_api, resources_cfg, lambda_map, authorizer_map)

            # ----------------- Create Usage Plan ----------------- #
            self._create_usage_plan(rest_api, api_cfg.get("usage_plan", {}), api_name)

            print(f"✅ REST API '{api_name}' created with resources: {list(resources_cfg.keys())}")

    def _create_resources_and_methods(self, rest_api, resources_cfg, lambda_map, authorizer_map):
        created_resources = {}
        for resource_name, cfg in resources_cfg.items():
            path_parts = cfg.get("resource_path", f"/{resource_name}").strip("/").split("/")
            parent_resource = rest_api.root
            current_path = ""
            for part in path_parts:
                if not part:
                    continue
                current_path = f"{current_path}/{part}" if current_path else part
                if current_path in created_resources:
                    parent_resource = created_resources[current_path]
                else:
                    parent_resource = parent_resource.add_resource(part)
                    created_resources[current_path] = parent_resource
            resource = parent_resource

            # Handle CORS
            if cfg.get("cors_enabled", False):
                resource.add_cors_preflight(
                    allow_origins=apigw.Cors.ALL_ORIGINS,
                    allow_methods=apigw.Cors.ALL_METHODS,
                    allow_headers=[
                        "Content-Type",
                        "X-Amz-Date",
                        "Authorization",
                        "X-Api-Key",
                        "X-Amz-Security-Token",
                        "authorizationToken",
                    ],
                )

            # Lambda integration
            lambda_fn_name = cfg.get("function_name")
            lambda_fn = lambda_map.get(lambda_fn_name)
            if not lambda_fn:
                print(f"⚠️ Lambda '{lambda_fn_name}' not found for resource '{resource_name}', skipping methods.")
                continue

            lambda_integration = apigw.LambdaIntegration(lambda_fn, proxy=True, allow_test_invoke=True)
            methods = cfg.get("methods", [])
            authorizations = cfg.get("authorization", {})

            for method in methods:
                method_upper = method.upper()
                if method_upper == "OPTIONS":
                    continue
                auth_name = authorizations.get(method_upper)
                authorizer = authorizer_map.get(auth_name) if auth_name else None
                auth_type = apigw.AuthorizationType.CUSTOM if authorizer else apigw.AuthorizationType.NONE
                resource.add_method(
                    method_upper,
                    lambda_integration,
                    api_key_required=method_upper in cfg.get("require_api_key", []),
                    authorization_type=auth_type,
                    authorizer=authorizer,
                )

    def _create_usage_plan(self, rest_api, usage_cfg, api_name):
        if not usage_cfg:
            return
        plan = apigw.UsagePlan(
            self,
            f"usage_planRestApi_{api_name.replace('-', '')}",
            name=f"{api_name}-usage-plan",
            throttle=apigw.ThrottleSettings(
                rate_limit=usage_cfg.get("rate_limit", 100),
                burst_limit=usage_cfg.get("burst_limit", 20),
            ),
            quota=apigw.QuotaSettings(
                limit=usage_cfg.get("limit", 1000),
                period=apigw.Period[usage_cfg.get("period", "MONTH").upper()],
            ),
        )
        plan.add_api_stage(stage=rest_api.deployment_stage)

