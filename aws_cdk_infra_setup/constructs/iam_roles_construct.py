import os
import json
from aws_cdk import aws_iam as iam
from constructs import Construct


class IamRoleConstruct(Construct):
    def __init__(self, scope: Construct, id: str, *, iam_role_configs=None, project_root=None, **kwargs):
        # Only pass valid CDK kwargs to the base Construct
        super().__init__(scope, id, **kwargs)

        print(f"🔍 IamRoleConstruct: Received {len(iam_role_configs or [])} role configs")

        self.project_root = project_root
        self.iam_role_configs = iam_role_configs or []

        # Keep a dict to reference roles by role_name if needed
        self.roles = {}

        for role_data in self.iam_role_configs:
            try:
                role_name = role_data["role_name"]

                # Get trust policy JSON dict from loaded config
                trust_policy_json = role_data.get("trust_policy")
                assume_role_policy = iam.PolicyDocument.from_json(trust_policy_json) if trust_policy_json else None

                # Managed policies from dict {name: arn}
                managed_policies = [
                    iam.ManagedPolicy.from_managed_policy_arn(self, f"{role_name}-{name}", arn)
                    for name, arn in role_data.get("managed_policies", {}).items()
                ]

                # Inline policies dict {name: JSON dict}
                inline_policies = {
                    name: iam.PolicyDocument.from_json(policy_json)
                    for name, policy_json in role_data.get("inline_policies", {}).items()
                }

                # Create the IAM Role construct
                role = iam.Role(
                    self,
                    role_name,
                    role_name=role_name,
                    assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),  # You can make this configurable too
                    inline_policies=inline_policies,
                    managed_policies=managed_policies,
                    # Note: Do NOT use assume_role_policy param here; use 'assumed_by' with PolicyDocument instead
                )

                # Store role in dictionary for easy access later
                self.roles[role_name] = role
                print(f"✅ Created IAM role: {role_name}")

            except Exception as e:
                print(f"❌ Failed to create role {id + 1}: {e}")
                continue

            print(f"🔍 Total IAM roles created: {len(self.roles)}")
            print(f"🔍 Available roles: {list(self.roles.keys())}")

    # Optional helper if you want to load JSON files inside this construct later:
    def _resolve_file_path(self, path):
        if os.path.isabs(path):
            return path
        return os.path.join(self.project_root or os.getcwd(), path)
