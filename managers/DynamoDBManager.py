# managers/DynamoDBManager.py

import logging

import boto3

import config  # Import the config file

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DynamoDBManager:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None):
        """
        Initialize the DynamoDBManager with optional AWS credentials.
        If credentials are not provided, it uses the default IAM role credentials.
        """
        try:
            if aws_access_key_id and aws_secret_access_key:
                # Initialize with provided credentials
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    region_name=config.AWS_REGION,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token
                )
                logger.info("DynamoDB resource initialized with provided AWS credentials.")
            else:
                # Initialize using IAM role credentials
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    region_name=config.AWS_REGION
                )
                logger.info("DynamoDB resource initialized using IAM role credentials.")

            self.table = self.dynamodb.Table(config.DYNAMODB_TABLE_NAME)
            logger.info(f"Connected to DynamoDB table: {config.DYNAMODB_TABLE_NAME}")

        except Exception as e:
            logger.error(f"Error initializing DynamoDBManager: {e}")
            raise Exception(f"Error initializing DynamoDBManager: {str(e)}")

    def put_item(self, key_name: str, data_dict: dict) -> dict:
        """
        Insert or update an item in the DynamoDB table.
        """
        logger.info(f"Putting item into DB with key: {key_name}")
        item = {'id': key_name}
        item.update(data_dict)
        response = self.table.put_item(Item=item)
        logger.info(f"Item with key '{key_name}' upserted successfully")
        return response

    def get_item(self, key_name: str) -> dict:
        logger.info(f"Getting item from DB with key: {key_name}")
        ret_val = None
        response = self.table.get_item(Key={'id': key_name})
        if 'Item' in response:
            logger.info(f"Item with key '{key_name}' found")
            ret_val = response['Item']
        else:
            logger.info(f"Item with key '{key_name}' not found")

        return ret_val
