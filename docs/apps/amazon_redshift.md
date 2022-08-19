# AWS Redshift Connector

## General Design
AWS Redshift is a data warehouse product. https://aws.amazon.com/redshift/

Currently, customers who want to insert data to AWS Redshift generally use 1 method:
- Upload file to S3 and run a COPY command

We want to create a way for customers to insert data from Amperity directly to their AWS Redshift table. 

By using our AWS Redshift connector, Amperity will send an NDJSON file to an API Gateway, which triggers an AWS Lambda function to read the file, upload to the current user's S3 bucket, and copy the data to their Redshift table.

## Requirements
- AWS Lambda function
- AWS API Gateway
- AWS Redshift Table
- AWS S3 Bucket

Set the following environment variables:
- REDSHIFT_CLUSTER_ID
- REDSHIFT_DB_NAME
- REDSHIFT_DB_USER
- REDSHIFT_IAM_ROLE
- REDSHIFT_TABLE_NAME
- S3_BUCKET

Lambda must have the following permissions policies:
- AWSLambdaBasicExecutionRole
- AmazonRedshiftFullAccess
- AWSLambdaExecute
- AWSLambdaRole
- AmazonS3ReadOnlyAccess

## API Docs
- [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Botocore Custom Waiter](https://docs.aws.amazon.com/code-samples/latest/catalog/python-demo_tools-custom_waiter.py.html)

### Dev Testing
```
curl -X POST 'http://localhost:5555/lambda/amazon_redshift' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/amazon_redshift.ndjson", "callback_url": "http://api_destination:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'
```