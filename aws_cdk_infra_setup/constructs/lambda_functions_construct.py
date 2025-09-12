from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_iam as iam
from aws_cdk import Duration
from constructs import Construct
import os


class LambdaFunctionConstruct(Construct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            *,
            iam_roles_construct=None,
            lambda_functions_config_files=None,
            project_root=None,
            **kwargs
    ):
        super().__init__(scope, id)

        if lambda_functions_config_files is None:
            lambda_functions_config_files = []

        runtime_map = {
            "python3.13": _lambda.Runtime.PYTHON_3_13,
            "python3.10": _lambda.Runtime.PYTHON_3_10,
            "python3.9": _lambda.Runtime.PYTHON_3_9,
            "python3.8": _lambda.Runtime.PYTHON_3_8,
            "python3.7": _lambda.Runtime.PYTHON_3_7,
        }

        # Dictionary to store created Lambda functions
        self.lambda_functions = {}

        for lambda_data in lambda_functions_config_files:
            try:
                service = lambda_data.get("service", {})

                function_name = service.get("function_name")
                role_name = service.get("role_name")
                handler = service.get("handler")
                runtime_str = service.get("runtime")
                zip_path = service.get("zip_file")
                timeout = service.get("timeout", 30)  # Default 30 seconds
                memory_size = service.get("memory_size", 128)  # Default 128 MB

                if not all([function_name, handler, runtime_str, zip_path]):
                    print(f"⚠️ Skipping Lambda config '{function_name}' due to missing required fields.")
                    continue

                # 🔧 FIX: Better role resolution
                role = None
                if iam_roles_construct and role_name:
                    # Primary method: access from roles dictionary
                    if hasattr(iam_roles_construct, "roles") and iam_roles_construct.roles:
                        role = iam_roles_construct.roles.get(role_name)
                        if role:
                            print(f"✅ Found role '{role_name}' in roles dictionary for Lambda '{function_name}'")

                    # Fallback method: find by construct ID
                    if role is None:
                        role_construct = iam_roles_construct.node.try_find_child(role_name)
                        if isinstance(role_construct, iam.Role):
                            role = role_construct
                            print(f"✅ Found role '{role_name}' by construct ID for Lambda '{function_name}'")

                    # Debug: List available roles if not found
                    if role is None and hasattr(iam_roles_construct, "roles"):
                        available_roles = list(iam_roles_construct.roles.keys())
                        print(
                            f"⚠️ Role '{role_name}' not found for Lambda '{function_name}'. Available roles: {available_roles}")
                else:
                    print(f"⚠️ No IAM roles construct or role name provided for Lambda '{function_name}'")

                # Create default role if not found
                if role is None:
                    print(f"⚠️ Role '{role_name}' not found for Lambda '{function_name}', creating default role.")
                    role = iam.Role(
                        self,
                        f"{function_name}DefaultRole",
                        role_name=f"{function_name}-default-role",
                        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                        managed_policies=[
                            iam.ManagedPolicy.from_aws_managed_policy_name(
                                "service-role/AWSLambdaBasicExecutionRole"
                            )
                        ],
                    )
                else:
                    print(f"✅ Found role '{role_name}' for Lambda '{function_name}'")

                # Validate runtime
                runtime = runtime_map.get(runtime_str.lower())
                if not runtime:
                    print(f"⚠️ Unsupported runtime '{runtime_str}' for Lambda '{function_name}', using Python 3.13")
                    runtime = _lambda.Runtime.PYTHON_3_13

                # Resolve code path
                code_path = zip_path
                if project_root and not os.path.isabs(zip_path):
                    code_path = os.path.join(project_root, zip_path)

                # Verify code path exists
                if not os.path.exists(code_path):
                    print(f"⚠️ Code path '{code_path}' does not exist for Lambda '{function_name}', skipping.")
                    continue

                # Create Lambda function with enhanced configuration
                func = _lambda.Function(
                    self,
                    id=f"{function_name}Function",
                    function_name=function_name,
                    runtime=runtime,
                    handler=handler,
                    code=_lambda.Code.from_asset(code_path),
                    role=role,
                    timeout=Duration.seconds(timeout),
                    memory_size=memory_size,
                    environment=service.get("environment_variables", {}),
                    description=service.get("description", f"Lambda function {function_name}"),
                    **kwargs
                )

                # Store function by function name
                self.lambda_functions[function_name] = func
                print(f"✅ Created Lambda function: {function_name}")

            except Exception as e:
                function_name = lambda_data.get("service", {}).get("function_name", "unknown")
                print(f"⚠️ Failed to create Lambda function '{function_name}': {str(e)}")
                continue

        print(f"🔹 Total Lambda functions created: {len(self.lambda_functions)}")