#!/bin/bash
set -e

echo "Waiting for DynamoDB Local to be ready..."
sleep 5

echo "Installing AWS CLI..."
pip3 install awscli-local awscli boto3 --quiet

# Set dummy AWS credentials (required by AWS CLI)
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export AWS_DEFAULT_REGION=us-east-1

echo "Creating kyc_sessions table..."
aws dynamodb create-table \
  --table-name kyc_sessions \
  --attribute-definitions AttributeName=reference,AttributeType=S \
  --key-schema AttributeName=reference,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://dynamodb-local:8000 \
  --region us-east-1 \
  || echo "Table might already exist"

echo "✅ DynamoDB initialization complete!"

# List tables to verify
aws dynamodb list-tables \
  --endpoint-url http://dynamodb-local:8000 \
  --region us-east-1
