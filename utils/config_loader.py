# aws_cdk_infra_setup/config_loader.py
import os
from aws_cdk import App


def load_stage_config(app: App, stage_name: str = None):
    """
    Load stage-specific and variable config from cdk.json.
    Returns a merged dict containing region, account_id, secrets_file, and variables.
    """
    # Determine stage from argument, env, or default to "dev"
    stage = stage_name or app.node.try_get_context("stage") or os.getenv("STAGE") or "dev"

    stages_ctx = app.node.try_get_context("stages") or {}
    variables_ctx = app.node.try_get_context("variables") or {}

    stage_config = stages_ctx.get(stage, {})
    stage_variables = variables_ctx.get(stage, {})

    # Merge variables into stage config
    merged = {**stage_config, "variables": stage_variables}
    merged["stage_name"] = stage

    return merged
