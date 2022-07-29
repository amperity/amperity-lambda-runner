# Microsoft Dataverse Connector

## General Design
Dataverse lets you securely store and manage data that's used by business applications.
https://docs.microsoft.com/en-us/power-apps/maker/data-platform/data-platform-intro

By using our Microsoft Dataverse connector, Amperity will send data to an API Gateway which will trigger a Lambda function to validate each row of data and if valid, will insert the row into the chosen table.

## Requirements
- AWS Lambda function
- AWS API Gateway
- Microsoft Dataverse table

## Getting Started

### Setup authentication

1. In Azure Active Directory, go to [App Registrations](https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps)
2. Click "New Registration" , name your app, and leave everything else as default. Click "Register"
3. On your new app's overview page, copy the "Application (client) ID" and "Directory (tenant) ID" to your environment variables.
4. On the left side, click "Authentication", "Add a platform", then "Web"

    a. In the Redirect URIs field, enter "https://app.amperity.com"

    b. Under "Implicit grant and hybrid flows", check "Access tokens (used for implicit flows)" and click "Configure".
5. On the left side, click "Certificates & secrets"

    a. Under the "Client secrets" tab, click "New client secret" to create a new secret.

    b. Copy your secret value to your environment variables.
6. On the left side, click "API permissions"

    a. Click "Add a permission", "Dynamics CRM", check "user_impersonation", then click "Add permissions"
7. Go to https://admin.powerplatform.microsoft.com/, click "Environments", and click on your environment.

    a. Click on "Settings", "Users and permissions", then "Application users"

    b. Click on "New app user" and select the app you just created, your business unit, and under "Security roles", click the edit button.

    c. Select "Service Reader" and "Service Writer", click "Save", then click "Create".

8. You are now ready to run your connector!

Set the following environment variables:
- ORG_ID
- ORG_REGION
- TENANT_ID
- CLIENT_ID
- CLIENT_SECRET

## API Docs
- [Microsoft Web API HTTP Requests](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/compose-http-requests-handle-errors)
- [MSAL Authentication](https://github.com/AzureAD/microsoft-authentication-library-for-python/blob/dev/sample/confidential_client_secret_sample.py)

## Dev Testing
```
curl -X POST 'http://localhost:5555/lambda/dataverse' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/dataverse.ndjson", "callback_url": "http://api_destination:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'
```