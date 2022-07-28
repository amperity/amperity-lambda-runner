# Microsoft Dataverse Connector

## General Design
Dataverse lets you securely store and manage data that's used by business applications.
https://docs.microsoft.com/en-us/power-apps/maker/data-platform/data-platform-intro

By using our Microsoft Dataverse connector, Amperity will send data to an API Gateway which will trigger a Lambda function to validate each row of data and if valid, will insert the row into the chosen table.

## Requirements
- AWS Lambda function
- AWS API Gateway
- Microsoft Dataverse table

Set the following environment variables:
- ORG_ID
- ORG_REGION
- TENANT_ID
- CLIENT_ID
- CLIENT_SECRET

## API Docs
- [Microsoft Web API HTTP Requests](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/compose-http-requests-handle-errors)
- [MSAL Authentication](https://github.com/AzureAD/microsoft-authentication-library-for-python/blob/dev/sample/confidential_client_secret_sample.py)