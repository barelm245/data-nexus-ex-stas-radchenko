import boto3
import json
from botocore.exceptions import ClientError
import config
import logging

logger = logging.getLogger(__name__)

with open('secrets.json') as r:
    try:
        aws_secrets = json.loads(r.read())
    except FileNotFoundError:
        logger.error("'secrets.json' file not found")
        aws_secrets = None

class S3Manager:
    def __init__(self):
        logger.info("Initializing S3Manager")
        if aws_secrets:
            try:
                self.s3 = boto3.client('s3', region_name=config.AWS_REGION,
                                       aws_access_key_id=aws_secrets["AWS_ACCESS_KEY_ID"],
                                       aws_secret_access_key=aws_secrets["AWS_SECRET_ACCESS_KEY"],
                                       aws_session_token=aws_secrets["AWS_SESSION_TOKEN"])
                logger.info("S3 client initialized with credentials from secrets.json")
            except KeyError:
                logger.error("Missing required AWS credentials in 'secrets.json'")
                raise Exception("Error: Missing required AWS credentials in 'secrets.json'")
        else:
            logger.error("AWS credentials not found in 'secrets.json'")
            raise Exception("Error: AWS credentials not found. Please provide a valid 'secrets.json'.")

    def get_file_from_s3(self, s3_path: str) -> bytes:
        logger.info(f"Getting file from S3: {s3_path}")
        try:
            # Parse S3 path
            parts = self.extract_s3_path_attributes(s3_path)

            bucket_name = parts[0]
            object_key = parts[1]

            # Get object from S3
            response = self.s3.get_object(Bucket=bucket_name, Key=object_key)

            logger.info(f"Fetched object from bucket={bucket_name} key={object_key}")
            # Return the file content as bytes
            return response['Body'].read()

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 ClientError {error_code} for path: {s3_path}")
            if error_code == 'NoSuchKey':
                raise Exception(f"File not found in S3: {s3_path}")
            elif error_code == 'AccessDenied':
                raise Exception(f"Access denied to S3 file: {s3_path}")
            else:
                raise Exception(f"Error fetching file from S3: {str(e)}")
        except Exception as e:
            logger.exception(f"Error fetching file from S3: {s3_path}")
            raise Exception(f"Error fetching file from S3: {str(e)}")

    def upload_json_to_s3(self, s3_path: str, json_data: dict) -> None:
        logger.info(f"Uploading JSON to S3: {s3_path}")
        try:
            # Parse S3 path
            parts = self.extract_s3_path_attributes(s3_path)

            bucket_name = parts[0]
            object_key = parts[1]

            # Convert dict to JSON string
            json_string = json.dumps(json_data)

            # Upload JSON string to S3
            self.s3.put_object(Bucket=bucket_name, Key=object_key, Body=json_string, ContentType='application/json')
            logger.info(f"Uploaded JSON to bucket={bucket_name} key={object_key}")

        except ClientError as e:
            logger.exception(f"ClientError uploading JSON to S3: {s3_path}")
            raise Exception(f"Error uploading JSON to S3: {str(e)}")
        except Exception as e:
            logger.exception(f"Error uploading JSON to S3: {s3_path}")
            raise Exception(f"Error uploading JSON to S3: {str(e)}")

    def extract_s3_path_attributes(self, s3_path: str) -> list[str]:
        logger.debug(f"Parsing S3 path: {s3_path}")
        if not s3_path.startswith('s3://'):
            logger.error(f"Invalid S3 path format: {s3_path}")
            raise ValueError("Invalid S3 path format. Must start with 's3://'")

        # Remove 's3://' prefix and split into bucket and key
        path_without_prefix = s3_path[5:]
        parts = path_without_prefix.split('/', 1)

        if len(parts) != 2:
            logger.error(f"Invalid S3 path structure: {s3_path}")
            raise ValueError("Invalid S3 path format. Must be 's3://bucket-name/path/to/file'")
        logger.debug(f"Parsed S3 path into bucket={parts[0]} key={parts[1]}")
        return parts
