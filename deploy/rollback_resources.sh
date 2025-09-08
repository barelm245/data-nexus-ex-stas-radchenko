#!/bin/bash

# Do not exit on error; continue attempting all steps even if some fail
set +e

# Load secrets.json
AWS_ACCESS_KEY_ID=$(jq -r '.AWS_ACCESS_KEY_ID' secrets.json)
AWS_SECRET_ACCESS_KEY=$(jq -r '.AWS_SECRET_ACCESS_KEY' secrets.json)
AWS_SESSION_TOKEN=$(jq -r '.AWS_SESSION_TOKEN' secrets.json)

# Load config.py for constants
LAMBDA_ROLE_NAME=$(python -c "import config; print(config.LAMBDA_ROLE_NAME)")
LAMBDA_FUNCTION_NAME=$(python -c "import config; print(config.LAMBDA_FUNCTION_NAME)")
S3_BUCKET_NAME=$(python -c "import config; print(config.S3_BUCKET_NAME)")
DYNAMODB_TABLE_NAME=$(python -c "import config; print(config.DYNAMODB_TABLE_NAME)")
REGION=$(python -c "import config; print(config.AWS_REGION)")

# Export AWS credentials for CLI use
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN

# Step 1: Remove Lambda permission for S3 to invoke it (ignore if not present)
echo "Removing S3 invocation permission from Lambda..."
aws lambda remove-permission --function-name $LAMBDA_FUNCTION_NAME --statement-id AllowS3InvokeLambda --region $REGION --no-cli-pager || {
  echo "No permission found for S3 invocation. Skipping removal."
}

# Step 2: Remove S3 event trigger for Lambda
echo "Removing S3 event trigger..."
aws s3api put-bucket-notification-configuration \
  --bucket $S3_BUCKET_NAME \
  --notification-configuration '{}' \
  --region $REGION --no-cli-pager || {
    echo "Failed to remove S3 event trigger."
  }
echo "S3 event trigger removed."

# Step 3: Delete Lambda function
EXISTS=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.FunctionName' --output text 2>/dev/null --region $REGION --no-cli-pager)

if [ "$EXISTS" == "$LAMBDA_FUNCTION_NAME" ]; then
  echo "Deleting Lambda function $LAMBDA_FUNCTION_NAME..."
  aws lambda delete-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION --no-cli-pager || {
    echo "Failed to delete Lambda function."
  }
  echo "Lambda function deleted."
else
  echo "Lambda function $LAMBDA_FUNCTION_NAME does not exist. Skipping deletion."
fi

# Step 4: Detach policies and delete IAM role
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query "Role.Arn" --output text 2>/dev/null --region $REGION --no-cli-pager)

if [ ! -z "$ROLE_ARN" ]; then
  echo "Detaching policies from IAM role $LAMBDA_ROLE_NAME..."
  
  # Detach AWSLambdaBasicExecutionRole policy
  aws iam detach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --region $REGION --no-cli-pager 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Warning: Failed to detach AWSLambdaBasicExecutionRole or it was not attached."
  else
    echo "Successfully detached AWSLambdaBasicExecutionRole."
  fi
  
  # Detach AmazonS3FullAccess policy
  aws iam detach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess --region $REGION --no-cli-pager 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Warning: Failed to detach AmazonS3FullAccess or it was not attached."
  else
    echo "Successfully detached AmazonS3FullAccess."
  fi

  # Detach AmazonDynamoDBFullAccess policy
  aws iam detach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess --region $REGION --no-cli-pager 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Warning: Failed to detach AmazonDynamoDBFullAccess or it was not attached."
  else
    echo "Successfully detached AmazonDynamoDBFullAccess."
  fi
  
  # Deleting the IAM role
  echo "Deleting IAM role $LAMBDA_ROLE_NAME..."
  aws iam delete-role --role-name $LAMBDA_ROLE_NAME --region $REGION --no-cli-pager || {
    echo "Failed to delete IAM role $LAMBDA_ROLE_NAME."
  }
  echo "IAM role deleted."
else
  echo "IAM role $LAMBDA_ROLE_NAME does not exist. Skipping deletion."
fi

# Step 5: Delete DynamoDB table
TABLE_EXISTS=$(aws dynamodb describe-table --table-name $DYNAMODB_TABLE_NAME --query 'Table.TableName' --output text 2>/dev/null --region $REGION --no-cli-pager)

if [ "$TABLE_EXISTS" == "$DYNAMODB_TABLE_NAME" ]; then
  echo "Deleting DynamoDB table $DYNAMODB_TABLE_NAME..."
  aws dynamodb delete-table --table-name $DYNAMODB_TABLE_NAME --region $REGION --no-cli-pager || {
    echo "Failed to delete DynamoDB table."
  }
  echo "Waiting for DynamoDB table deletion..."
  aws dynamodb wait table-not-exists --table-name $DYNAMODB_TABLE_NAME --region $REGION --no-cli-pager || {
    echo "Failed to wait for DynamoDB table deletion."
  }
  echo "DynamoDB table deleted."
else
  echo "DynamoDB table $DYNAMODB_TABLE_NAME does not exist. Skipping deletion."
fi

# Step 6: Delete the zip file and s3_lambda_notification.json
echo "Cleaning up deployment artifacts..."

if [ -f "deploy/lambda_function.zip" ]; then
  echo "Deleting lambda_function.zip"
  if rm -v "deploy/lambda_function.zip"; then
    echo "lambda_function.zip successfully deleted."
  else
    echo "Failed to delete lambda_function.zip. Checking file permissions..."
    ls -l "deploy/lambda_function.zip"
  fi
else
  echo "lambda_function.zip not found."
fi

if [ -f "deploy/s3_lambda_notification.json" ]; then
  echo "Deleting s3_lambda_notification.json"
  if rm -v "deploy/s3_lambda_notification.json"; then
    echo "s3_lambda_notification.json successfully deleted."
  else
    echo "Failed to delete s3_lambda_notification.json. Checking file permissions..."
    ls -l "deploy/s3_lambda_notification.json"
  fi
else
  echo "s3_lambda_notification.json not found."
fi

echo "Rollback complete!"
