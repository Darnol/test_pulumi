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
    environment={"variables": {"EXTERNAL_URL": "https://meme-api.com/gimme"}},
)

# === API Gateway V1 (REST API) ===
api = aws.apigateway.RestApi(
    "restApi", description="API Gateway V1 with Lambda Integration"
)

# Resource: /get-meme
resource = aws.apigateway.Resource(
    "getMemeResource",
    rest_api=api.id,
    parent_id=api.root_resource_id,
    path_part="get-meme",
)

# Method: GET
method = aws.apigateway.Method(
    "getMemeMethod",
    rest_api=api.id,
    resource_id=resource.id,
    http_method="GET",
    authorization="NONE",
)

# Integration with Lambda
integration = aws.apigateway.Integration(
    "lambdaIntegration",
    rest_api=api.id,
    resource_id=resource.id,
    http_method=method.http_method,
    integration_http_method="POST",
    type="AWS_PROXY",
    uri=lambda_function.invoke_arn,
)

# Deployment
deployment = aws.apigateway.Deployment(
    "apiDeployment",
    rest_api=api.id,
    triggers={"redeployment": pulumi.Output.all(resource.id, integration.id)},
    opts=pulumi.ResourceOptions(depends_on=[integration]),
)

# Stage
stage = aws.apigateway.Stage(
    "apiStage", rest_api=api.id, deployment=deployment.id, stage_name="dev"
)

# Lambda permission for API Gateway
aws.lambda_.Permission(
    "apiLambdaPermission",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="apigateway.amazonaws.com",
    source_arn=pulumi.Output.concat(api.execution_arn, "/*"),
)

# Export the API URL and the static website
pulumi.export(
    "api_url",
    pulumi.Output.concat(
        "https://",
        api.id,
        ".execute-api.",
        aws.config.region,
        ".amazonaws.com/dev/get-meme",
    ),
)
pulumi.export("website_url", bucket.website_endpoint)

# # Export the name of the bucket
# pulumi.export(
#     "bucket_endpoint", pulumi.Output.concat("http://", website.website_endpoint)
# )
