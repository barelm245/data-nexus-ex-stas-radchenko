# managers/DynamoDBManager.py

import boto3
import config  # Import the config file
import json
import logging

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
