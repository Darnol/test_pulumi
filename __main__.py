"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws
import json
from lambda_fct.make_layer import make_layer


###
# Lambda Function
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
    code=pulumi.AssetArchive({".": pulumi.FileArchive("./lambda_fct")}),
    environment={"variables": {"EXTERNAL_URL": "https://meme-api.com/gimme"}},
)


###
# === API Gateway V1 (REST API) ===
api = aws.apigateway.RestApi(
    "restApi", description="API Gateway V1 with Lambda Integration"
)

# Resource: /getmeme
resource = aws.apigateway.Resource(
    "getMemeResource",
    rest_api=api.id,
    parent_id=api.root_resource_id,
    path_part="getmeme",
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

###
# S3 and Website
# === Generate script.js Dynamically ===
api_url = pulumi.Output.concat(
    "https://",
    api.id,
    ".execute-api.",
    aws.config.region,
    ".amazonaws.com/dev/getmeme",
)

script_content = pulumi.Output.format(
    """
const button = document.getElementById("getMemeBtn");
const memeImage = document.getElementById("memeImage");

const apiUrl = "{0}";

button.addEventListener("click", async () => {{
    try {{
        const response = await fetch(apiUrl);
        const data = await response.json();
        memeImage.src = data.meme_url;
        memeImage.style.display = "block";
    }} catch (error) {{
        console.error("Error fetching meme:", error);
    }}
}});
""",
    api_url,
)

# Write the dynamically generated script to the bucket
bucket = aws.s3.Bucket("staticSiteBucket", website={"index_document": "index.html"})

index_html = aws.s3.BucketObject(
    "indexHtml",
    bucket=bucket.id,
    source=pulumi.FileAsset("website/index.html"),
    content_type="text/html",
)

script_js = aws.s3.BucketObject(
    "scriptJs",
    bucket=bucket.id,
    content=script_content,
    content_type="application/javascript",
)

# Export Outputs
pulumi.export("api_url", api_url)
pulumi.export("website_url", bucket.website_endpoint)
