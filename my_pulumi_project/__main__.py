"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws
import json
import requests

# Create an AWS resource (S3 Bucket)
bucket = aws.s3.BucketV2("my-bucket")

website = aws.s3.BucketWebsiteConfigurationV2(
    "website",
    bucket=bucket.id,
    index_document={
        "suffix": "index.html",
    },
)

# Create an S3 Bucket object
ownership_controls = aws.s3.BucketOwnershipControls(
    "ownership-controls",
    bucket=bucket.id,
    rule={
        "object_ownership": "ObjectWriter",
    },
)

public_access_block = aws.s3.BucketPublicAccessBlock(
    "public-access-block", bucket=bucket.id, block_public_acls=False
)

bucket_object = aws.s3.BucketObject(
    "index.html",
    bucket=bucket.id,
    source=pulumi.FileAsset("index.html"),
    content_type="text/html",
    acl="public-read",
    opts=pulumi.ResourceOptions(
        depends_on=[public_access_block, ownership_controls, website]
    ),
)

# Lambda function: fetch external resource
lambda_role = aws.iam.Role(
    "lambdaRole",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Effect": "Allow",
                }
            ],
        }
    ),
)

# Attach Lambda policy for logging
aws.iam.RolePolicyAttachment(
    "lambdaLogs",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

# Lambda Function
lambda_function = aws.lambda_.Function(
    "fetchResourceFunction",
    role=lambda_role.arn,
    runtime="python3.11",
    handler="handler.lambda_handler",
    code=pulumi.AssetArchive({".": pulumi.FileArchive("./lambda")}),
    environment={"variables": {"EXTERNAL_URL": "https://example.com/resource"}},
)

# API Gateway
api = aws.apigatewayv2.Api("httpApi", protocol_type="HTTP")

# API Integration with Lambda
integration = aws.apigatewayv2.Integration(
    "httpApiIntegration",
    api_id=api.id,
    integration_type="AWS_PROXY",
    integration_method="POST",
    integration_uri=lambda_function.invoke_arn,
)

# Route
route = aws.apigatewayv2.Route(
    "httpApiRoute",
    api_id=api.id,
    route_key="GET /fetch-resource",
    target=pulumi.Output.concat("integrations/", integration.id),
)

# Deploy API
stage = aws.apigatewayv2.Stage(
    "httpApiStage", api_id=api.id, name="$default", auto_deploy=True
)

# Grant permission for API Gateway to invoke the Lambda
aws.lambda_.Permission(
    "apiLambdaPermission",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="apigateway.amazonaws.com",
    source_arn=pulumi.Output.concat(api.execution_arn, "/*"),
)

# Export the API URL
pulumi.export("api_endpoint", api.api_endpoint)

# # Export the name of the bucket
# pulumi.export(
#     "bucket_endpoint", pulumi.Output.concat("http://", website.website_endpoint)
# )
