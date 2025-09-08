#!/bin/bash

# Exit on non-zero status disabled, we want to keep going even if some steps fail
set +e

# Load secrets.json (from the root folder)
AWS_ACCESS_KEY_ID=$(jq -r '.AWS_ACCESS_KEY_ID' secrets.json)
AWS_SECRET_ACCESS_KEY=$(jq -r '.AWS_SECRET_ACCESS_KEY' secrets.json)
AWS_SESSION_TOKEN=$(jq -r '.AWS_SESSION_TOKEN' secrets.json)

# Check if secrets.json was loaded correctly
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_SESSION_TOKEN" ]; then
  echo "Warning: Failed to load AWS credentials from secrets.json. Continuing, but expect errors."
fi

# Load config.py for constants
LAMBDA_ROLE_NAME=$(python -c "import config; print(config.LAMBDA_ROLE_NAME)")
LAMBDA_FUNCTION_NAME=$(python -c "import config; print(config.LAMBDA_FUNCTION_NAME)")
S3_BUCKET_NAME=$(python -c "import config; print(config.S3_BUCKET_NAME)")
DYNAMODB_TABLE_NAME=$(python -c "import config; print(config.DYNAMODB_TABLE_NAME)")
REGION=$(python -c "import config; print(config.AWS_REGION)")

# Exit if any of the config variables are not set
if [ -z "$LAMBDA_ROLE_NAME" ] || [ -z "$LAMBDA_FUNCTION_NAME" ] || [ -z "$S3_BUCKET_NAME" ] || [ -z "$DYNAMODB_TABLE_NAME" ] || [ -z "$REGION" ]; then
  echo "Error: Failed to load config variables from config.py. Continuing, but expect errors."
fi

# Export AWS credentials for CLI use
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN

echo "Starting Deployment Process..."

# Step 1: Check for existing IAM role for Lambda
echo "Checking if IAM Role exists..."
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query "Role.Arn" --output text 2>/dev/null --region $REGION --no-cli-pager)

if [ -z "$ROLE_ARN" ]; then
  echo "Creating Lambda IAM role..."
  aws iam create-role \
    --role-name $LAMBDA_ROLE_NAME \
    --assume-role-policy-document file://deploy/trust-policy.json \
    --region $REGION --no-cli-pager

  # Attach policies for S3, DynamoDB, and Lambda execution
  aws iam attach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --region $REGION --no-cli-pager
  aws iam attach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess --region $REGION --no-cli-pager
  aws iam attach-role-policy --role-name $LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess --region $REGION --no-cli-pager

  # Wait for the role to propagate
  sleep 10

  ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query "Role.Arn" --output text --region $REGION --no-cli-pager)
  echo "IAM Role created: $ROLE_ARN"
else
  echo "IAM Role already exists: $ROLE_ARN"
fi

# Step 2: Check for existing DynamoDB table
echo "Checking if DynamoDB table exists..."
TABLE_EXISTS=$(aws dynamodb describe-table --table-name $DYNAMODB_TABLE_NAME --query 'Table.TableName' --output text 2>/dev/null --region $REGION --no-cli-pager)

if [ "$TABLE_EXISTS" != "$DYNAMODB_TABLE_NAME" ]; then
  echo "Creating DynamoDB table $DYNAMODB_TABLE_NAME..."
  aws dynamodb create-table \
    --table-name $DYNAMODB_TABLE_NAME \
    --attribute-definitions AttributeName=FilePath,AttributeType=S \
    --key-schema AttributeName=FilePath,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION --no-cli-pager

  echo "Waiting for table creation..."
  aws dynamodb wait table-exists --table-name $DYNAMODB_TABLE_NAME --region $REGION --no-cli-pager
  echo "DynamoDB table $DYNAMODB_TABLE_NAME created."
else
  echo "DynamoDB table $DYNAMODB_TABLE_NAME already exists."
fi

# Step 3: Create zip package for Lambda deployment
# Step 3: Create zip package for Lambda deployment
echo "Creating Lambda function zip package..."
cd lambda # Navigate to the lambda directory
zip -r ../deploy/lambda_function.zip lambda_function.py ../config.py ../managers/DynamoDBManager.py # Create the ZIP package including relevant files.
cd .. # Navigate back to the root directory
if [ $? -ne 0 ]; then
  echo "Warning: Failed to create the Lambda zip package. Continuing."
fi

# Step 4: Check for existing Lambda function
echo "Checking if Lambda function exists..."
EXISTS=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.FunctionName' --output text 2>/dev/null --region $REGION --no-cli-pager)

# If the function exists but is in an invalid state, delete and recreate
if [ "$EXISTS" == "$LAMBDA_FUNCTION_NAME" ]; then
  STATE=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.State' --output text --region $REGION --no-cli-pager)
  if [ "$STATE" != "Active" ]; then
    echo "Lambda function exists but is in state $STATE. Deleting the function..."
    aws lambda delete-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION --no-cli-pager
    EXISTS=""
  fi
fi

# Create the Lambda function if it doesn't exist
if [ -z "$EXISTS" ]; then
  echo "Creating Lambda function $LAMBDA_FUNCTION_NAME..."
  CREATE_OUTPUT=$(aws lambda create-function \
    --function-name $LAMBDA_FUNCTION_NAME \
    --runtime python3.8 \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://deploy/lambda_function.zip \
    --timeout 10 \
    --region $REGION --no-cli-pager 2>&1) 
  if [ $? -ne 0 ]; then
      echo "Warning: Error creating Lambda function: $CREATE_OUTPUT"
  fi
else
  echo "Updating Lambda function $LAMBDA_FUNCTION_NAME..."
  UPDATE_OUTPUT=$(aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --zip-file fileb://deploy/lambda_function.zip \
    --region $REGION --no-cli-pager 2>&1)
  if [ $? -ne 0 ]; then
    echo "Warning: Error updating Lambda function: $UPDATE_OUTPUT"
  fi
fi

# Step 5: Wait for Lambda function to become active
echo "Waiting for Lambda function to become active..."
aws lambda wait function-active --function-name $LAMBDA_FUNCTION_NAME --region $REGION --no-cli-pager
echo "Lambda function is now active."

# Step 6: Check for existing permission and remove if necessary
echo "Checking if permission for S3 invocation exists..."
EXISTS=$(aws lambda get-policy --function-name $LAMBDA_FUNCTION_NAME --region $REGION --query 'Policy' --output text 2>/dev/null)

if [[ "$EXISTS" == *"AllowS3InvokeLambda"* ]]; then
  echo "Removing existing permission AllowS3InvokeLambda..."
  aws lambda remove-permission --function-name $LAMBDA_FUNCTION_NAME --statement-id AllowS3InvokeLambda --region $REGION --no-cli-pager || true
fi

# Step 7: Add permission for S3 to invoke Lambda
echo "Adding permission for S3 to invoke Lambda..."
aws lambda add-permission \
  --function-name $LAMBDA_FUNCTION_NAME \
  --principal s3.amazonaws.com \
  --statement-id AllowS3InvokeLambda \
  --action "lambda:InvokeFunction" \
  --source-arn arn:aws:s3:::$S3_BUCKET_NAME \
  --region $REGION --no-cli-pager
if [ $? -ne 0 ]; then
  echo "Warning: Failed to add permission for S3 to invoke Lambda. Continuing."
fi

# Step 8: Fetch the Lambda ARN dynamically
echo "Fetching the Lambda ARN..."
LAMBDA_ARN=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $REGION --no-cli-pager)

# Step 9: Dynamically create the S3 notification configuration with the Lambda ARN
echo "Creating S3 notification configuration..."
cat > deploy/s3_lambda_notification.json <<EOL
{
    "LambdaFunctionConfigurations": [
      {
        "LambdaFunctionArn": "$LAMBDA_ARN",
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {
          "Key": {
            "FilterRules": [
              {
                "Name": "suffix",
                "Value": ".json"
              }
            ]
          }
        }
      }
    ]
}
EOL

# Step 10: Set up S3 event trigger for Lambda
echo "Setting up S3 event trigger for Lambda..."
aws s3api put-bucket-notification-configuration \
  --bucket $S3_BUCKET_NAME \
  --notification-configuration file://deploy/s3_lambda_notification.json \
  --region $REGION --no-cli-pager
if [ $? -ne 0 ]; then
  echo "Warning: Failed to set up S3 event trigger for Lambda. Continuing."
fi

echo "Deployment complete!"
