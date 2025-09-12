import os
import json
import aws_cdk as cdk
from aws_cdk_infra_setup.aws_cdk_infra_setup_stack import AwsCdkInfraSetupStack
from utils.json_loader import JsonLoader


# ----------------- Helpers ----------------- #
def resolve_file_path(file_path: str, project_root: str) -> str:
    """Resolve file path relative to project root if not absolute"""
    return file_path if os.path.isabs(file_path) else os.path.join(project_root, file_path)


def load_iam_role_config(file_path: str, project_root: str) -> dict:
    """Load IAM role configuration with trust policy and inline policies"""
    print(f"🔍 Loading role config from: {file_path}")

    full_path = resolve_file_path(file_path, project_root)
    data = JsonLoader.load_json(full_path)
    print(f"🔍 Role name: {data.get('role_name')}")

    # Load trust policy JSON inline
    trust_policy_path = data.pop("trust_policy_path", None)
    if trust_policy_path:
        try:
            trust_policy_full_path = resolve_file_path(trust_policy_path, project_root)
            data["trust_policy"] = JsonLoader.load_json(trust_policy_full_path)
            print(f"✅ Trust policy loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load trust policy: {e}")
            data["trust_policy"] = None
    else:
        data["trust_policy"] = None

    # Load inline policies JSON inline
    inline_policy_files = data.pop("inline_policy_files", [])
    inline_policies = {}

    for inline_file in inline_policy_files:
        print(f"🔍 Loading inline policy from: {inline_file}")
        try:
            inline_policy_full_path = resolve_file_path(inline_file, project_root)
            policy_json = JsonLoader.load_json(inline_policy_full_path)
            policy_name = os.path.splitext(os.path.basename(inline_file))[0]
            inline_policies[policy_name] = policy_json
            print(f"✅ Inline policy '{policy_name}' loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load inline policy '{inline_file}': {e}")

    data["inline_policies"] = inline_policies
    return data


def load_lambda_function_config(file_path: str, project_root: str) -> dict:
    """Load Lambda function configuration"""
    full_path = resolve_file_path(file_path, project_root)
    return JsonLoader.load_json(full_path)


def load_rest_api_config(file_path: str, project_root: str) -> dict:
    """Load REST API Gateway configuration"""
    full_path = resolve_file_path(file_path, project_root)
    return JsonLoader.load_json(full_path)


def load_http_api_config(file_path: str, project_root: str) -> dict:
    """Load HTTP API Gateway configuration"""
    full_path = resolve_file_path(file_path, project_root)
    return JsonLoader.load_json(full_path)


def load_cognito_user_pool_config(file_path: str, project_root: str) -> dict:
    """Load Cognito User Pool configuration"""
    full_path = resolve_file_path(file_path, project_root)
    return JsonLoader.load_json(full_path)


# def load_cognito_identity_pool_config(file_path: str, project_root: str) -> dict:
#     """Load Cognito Identity Pool configuration"""
#     full_path = resolve_file_path(file_path, project_root)
#     return JsonLoader.load_json(full_path)


def load_config_files(config_files: list, loader_func, project_root: str) -> list:
    """Generic function to load multiple configuration files with detailed error reporting"""
    loaded_configs = []
    failed_files = []

    for file_path in config_files:
        try:
            config = loader_func(file_path, project_root)
            loaded_configs.append(config)
            print(f"✅ Loaded: {file_path}")
        except FileNotFoundError as e:
            failed_files.append(file_path)
            print(f"❌ File not found: {file_path}")
        except Exception as e:
            failed_files.append(file_path)
            print(f"❌ Error loading {file_path}: {e}")

    if failed_files:
        print(f"\n🚨 Failed to load {len(failed_files)} configuration files:")
        for failed_file in failed_files:
            full_path = resolve_file_path(failed_file, project_root)
            print(f"   - {failed_file}")
            print(f"     Expected at: {full_path}")

        # List existing files in the directory for debugging
        for failed_file in failed_files:
            dir_path = os.path.dirname(resolve_file_path(failed_file, project_root))
            if os.path.exists(dir_path):
                existing_files = os.listdir(dir_path)
                print(f"     Files in directory: {existing_files}")

        raise FileNotFoundError(f"Configuration files missing: {failed_files}")

    return loaded_configs


# ----------------- Entry point ----------------- #
app = cdk.App()
project_root = os.path.dirname(os.path.abspath(__file__))

# Load CDK context for stages, account, region
context = app.node.try_get_context("stages") or {}
active_stage = app.node.try_get_context("active_stage") or "dev"
stage_config = context.get(active_stage, {})

account = stage_config.get("account_id") or os.getenv("CDK_DEFAULT_ACCOUNT")
region = stage_config.get("region") or os.getenv("CDK_DEFAULT_REGION")
env = cdk.Environment(account=account, region=region)

# Get config file paths from CDK context
role_config_files = app.node.try_get_context("iam_roles_config_files") or []
lambda_config_files = app.node.try_get_context("lambda_functions_config_files") or []
rest_api_config_files = app.node.try_get_context("rest_api_gateway_config_files") or []
http_api_config_files = app.node.try_get_context("http_api_gateway_config_files") or []
user_pool_cognito_config_files = app.node.try_get_context("user_pool_cognito_config_files") or []
# identity_pool_cognito_config_files = app.node.try_get_context("identity_pool_cognito_config_files") or []

# Load all configurations using the utility functions
try:
    parsed_iam_role_configs = load_config_files(role_config_files, load_iam_role_config, project_root)
    parsed_lambda_function_configs = load_config_files(lambda_config_files, load_lambda_function_config, project_root)
    parsed_rest_api_configs = load_config_files(rest_api_config_files, load_rest_api_config, project_root)
    parsed_http_api_configs = load_config_files(http_api_config_files, load_http_api_config, project_root)
    parsed_user_pool_configs = load_config_files(user_pool_cognito_config_files, load_cognito_user_pool_config,
                                                 project_root)
    # parsed_identity_pool_configs = load_config_files(identity_pool_cognito_config_files,
    #                                                  load_cognito_identity_pool_config, project_root)

    print(f"✅ Successfully loaded all configuration files")

except FileNotFoundError as e:
    print(f"❌ Configuration file error: {e}")
    raise
except json.JSONDecodeError as e:
    print(f"❌ JSON parsing error: {e}")
    raise
except Exception as e:
    print(f"❌ Unexpected error loading configurations: {e}")
    raise

# ----------------- Instantiate the CDK stack ----------------- #
stack = AwsCdkInfraSetupStack(
    app,
    "AwsCdkInfraSetupStack",
    env=env,
    iam_role_configs=parsed_iam_role_configs,
    lambda_function_configs=parsed_lambda_function_configs,
    rest_api_configs=parsed_rest_api_configs,
    http_api_configs=parsed_http_api_configs,
    # user_pool_configs=parsed_user_pool_configs,
    # identity_pool_configs=parsed_identity_pool_configs,
    project_root=project_root
)

app.synth()

