import boto3
import json
import config  # Import the config file

with open('secrets.json') as r:
    try:
        aws_secrets = json.loads(r.read())
    except FileNotFoundError:
        print("Error: 'secrets.json' file not found.")
        aws_secrets = None

class S3Manager:
    def __init__(self):
        if aws_secrets:
            try:
                self.s3 = boto3.client('s3', region_name=config.AWS_REGION,
                                       aws_access_key_id=aws_secrets["AWS_ACCESS_KEY_ID"],
                                       aws_secret_access_key=aws_secrets["AWS_SECRET_ACCESS_KEY"],
                                       aws_session_token=aws_secrets["AWS_SESSION_TOKEN"])
            except KeyError:
                raise Exception("Error: Missing required AWS credentials in 'secrets.json'")
        else:
            raise Exception("Error: AWS credentials not found. Please provide a valid 'secrets.json'.")