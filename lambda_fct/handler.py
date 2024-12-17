import os
import requests


def lambda_handler(event, context):
    external_url = os.getenv("EXTERNAL_URL")

    if external_url is None:
        return {
            "statusCode": 500,
            "body": "EXTERNAL_URL environment variable not found in lambda_handler",
        }

    try:
        response = requests.get(external_url)
        return {
            "statusCode": 200,
            "body": response.text,
            "headers": {"Content-Type": "text/plain"},
        }
    except Exception as e:
        return {"statusCode": 500, "body": f"Error fetching resource: {str(e)}"}
