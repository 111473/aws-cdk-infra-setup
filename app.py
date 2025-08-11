#!/usr/bin/env python3

import aws_cdk as cdk

from aws_cdk_infra_setup.aws_cdk_infra_setup_stack import AwsCdkInfraSetupStack


app = cdk.App()
AwsCdkInfraSetupStack(app, "AwsCdkInfraSetupStack")

app.synth()
