import json
import boto3
import config
from managers.DynamoDBManager import DynamoDBManager
from models.DicomMetadata import DicomMetadata
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        # Initialize DynamoDB manager using IAM role credentials (no secrets needed in Lambda)
        dynamodb_manager = DynamoDBManager()

        # Initialize S3 client using IAM role
        s3_client = boto3.client('s3', region_name=config.AWS_REGION)

        # Process each record in the event (can be multiple files in batch)
        for record in event['Records']:
            # Extract S3 bucket and object key from the event
            bucket_name = record['s3']['bucket']['name']
            object_key = record['s3']['object']['key']

            # Log the processing
            logger.info(f"Processing file: s3://{bucket_name}/{object_key}")

            # Skip if not a JSON file in the json/ folder
            if not object_key.startswith('json/') or not object_key.endswith('.json'):
                logger.warning(f"Skipping non-JSON file or file not in json/ folder: {object_key}")
                continue

            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                json_content = response['Body'].read().decode('utf-8')

                metadata_dict = json.loads(json_content)
                metadata = DicomMetadata(**metadata_dict)

                # Derive the suffix (basename without .json) to use as the DynamoDB key
                basename = os.path.basename(object_key)  # e.g. 'anon-....json'
                name_without_ext, _ = os.path.splitext(basename)  # e.g. 'anon-...'

                # Use only the anon id (name_without_ext) as the DynamoDB item id
                key_name = name_without_ext

                # Optionally, keep the original JSON S3 path in the stored data
                s3_path = f"s3://{bucket_name}/{object_key}"

                dynamodb_manager.put_item(
                    key_name=key_name,
                    data_dict=metadata.model_dump(exclude_none=True)
                )

                logger.info(f"Successfully stored metadata for {key_name} in DynamoDB")
                logger.info(
                    f"Metadata: PatientID={metadata.PatientID}, StudyDate={metadata.StudyDate}, Modality={metadata.Modality}")

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from {object_key}: {str(e)}")
                raise
            except ValueError as e:
                logger.error(f"Invalid DicomMetadata format in {object_key}: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Error processing file {object_key}: {str(e)}")
                raise

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully processed JSON metadata and stored in DynamoDB'
            })
        }

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"Error processing S3 event: {str(e)}"
            })
        }