# AWS Pinpoint Connector

## General Design
Amazon Pinpoint is a flexible and scalable outbound and inbound marketing communications service. You can connect with customers over channels like email, SMS, push, voice or in-app messaging. 
https://aws.amazon.com/pinpoint/

By using our AWS Redshift connector, Amperity will send an NDJSON file (with phone numbers and messages) to an API Gateway which will trigger a Lambda function to validate each phone number, and if valid, send a text message to that phone number.

## Requirements
- AWS Lambda function
- AWS API Gateway

Set the following environment variables:
- PINPOINT_APP_ID
- PINPOINT_ORIGINATION_NUMBER

Lambda must have the following permissions policies:
- [PinpointFullAccess](IAM/PinpointFullAccess.json)

## API Docs
- [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

### Dev Testing
```
curl -X POST 'http://localhost:5555/lambda/amazon_pinpoint' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/amazon_pinpoint.ndjson", "callback_url": "http://api_destination:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'
```