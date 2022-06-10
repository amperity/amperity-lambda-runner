import json

import boto3
import requests

"""
Notes on AWS Connect workflow/behavior

First off in AWS & boto3 docs the methods under 'Connect' are for setting up and managing a Connect instance NOT 
the customer/profile data. For that you need the 'CustomerProfiles' set of documentation.

The code below uses the API methods in CustomerProfiles to demonstrate how to upload exported data from Amperity 
to a Connect instance. Most of the field naming was done in the SQL query that is run in the orchestration job
but address data needs to be reshaped into a dict. Otherwise the workflow is straightforward and requires little
work. Throughout the code I left comments for improvements/next steps but generally the only other work that might
need to happen is implementing a truncate and load functionality.

How to add permissions to the lambda in AWS:
In AWS lambda go to 'Configuration -> Permissions' and click on the role associated with the lambda. Click the
'Add Permissions' dropdown, select 'Attach Policies', and finally select 'Create Policy'. In the visual editor 
select 'Profile' as the service, select 'ListProfiles' under List, select 'SearchProfiles' under Read, and 
['CreateProfile', 'DeleteProfile', 'UpdateProfile'] under write. Next check the box to allow these permissions
on the domains in your account and name this policy in the following screen. Finally search this policy and 
associate it with your lambda.

Finally when you upload the zip of this lambda you will have to update 2 things.
1) Set the timeout to at least 5 minutes 'Configuration -> General Configuration'
2) Set the Handler in 'Runtime Settings' to 'app.lambda_handler'
"""


# Pull from customer-profiles tab in AWS NOT overview tab
# NOTE - This could be passed in using 'settings' param or looked up using API methods
CONNECT_DOMAIN='amazon-connect-amperity-acme'


def lambda_handler(event, context):
    """
    curl to trigger local test:
    curl -X POST 'http://localhost:5555/lambda/aws_connect' \
        -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/{{ ndjson file }}", "settings": {}}'

    Example record:
    {
        "BirthDate": "1933-09-12",
        "AccountNumber": "a7c91377-d3ef-3364-8d02-381f15d2e237",
        "LastName": "Barnes",
        "EmailAddress": "abarnes@rushthomasanddudley.com",
        "FirstName": "Aaron",
        "PhoneNumber": "+1-046-394-6845x56517",
        "country": null,
        "city": "West Chop",
        "postal": "20975",
        "address": "2865 Thomas Ranch Close",
        "state": "MA"
    }
    """
    address_dict = {
        'address': 'Address1',
        'city': 'City',
        'state': 'State',
        'postal': 'PostalCode',
        'country': 'Country'
    }

    connect_client = boto3.client(
        'customer-profiles',
        region_name='us-east-1',
    )
    payload = json.loads(event['body'])
    settings = json.loads(payload['settings'])

    # Settings field is always in the payload. Check if it it has a key/value of 'truncate': True
    if settings.get('truncate'):
        truncate_connect_instance()

    # https://requests.readthedocs.io/en/latest/user/advanced/?highlight=body-content-workflow#body-content-workflow
    with requests.get(payload.get('data_url'), stream=True) as resp:
        print('Starting AWS Connect Upload')
        # https://requests.readthedocs.io/en/latest/user/advanced/?highlight=body-content-workflow#streaming-requests
        for line in resp.iter_lines():
            line_content = json.loads(line.decode('utf-8'))
            address_val = {}
            row_val = {}

            for key, val in line_content.items():
                # Connect doesn't support NoneTypes so we skip any missing values
                if not val:
                    continue

                if key in address_dict:
                    address_val[address_dict[key]] = val
                else:
                    row_val[key] = val

            row_val['Address'] = address_val

            connect_client.create_profile(
                DomainName=CONNECT_DOMAIN,
                PartyType='INDIVIDUAL',
                **row_val
            )

    print('Finished AWS Connect Upload')

    report_url = payload.get('callback_url') + payload.get('webhook_id')
    auth_str = f"Bearer {payload.get('access_token')}"

    callback_resp = requests.put(
        report_url,
        headers={
            'Content-Type': 'application/json',
            'X-Amperity-Tenant': 'noodles',
            'Authorization': auth_str
        }, 
        data=json.dumps({
            "state": "succeeded",
            "progress": 1
        })
    )

    if callback_resp.status_code != 200:
        print(callback_resp.status_code)
        print(callback_resp.content)

    print('Lambda Finished')
    
    return { 'statusCode': 200 }


def truncate_connect_instance():
    """
    Included is some psuedo code of a truncate and load functionality because there is no deduplication 
        out of the box in Connect. Two approaches are use these two API methods for a roundabout process or
        enable their 'Identity Resolution' feature and rely on it to upsert records correctly.

    NOTE KeyName is not using the same keys as are in the create endpoint. See link below for valid keynames
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/customer-profiles.html#CustomerProfiles.Client.search_profiles

    profiles = connect_client.search_profiles(
        DomainName=CONNECT_DOMAIN,
        KeyName='_account',
        # Create a list of all AccountNumber values and pass it in here.
        Values=['']
    )

    for profile in profiles:
        connect_client.delete_profile(
            DomainName=CONNECT_DOMAIN,
            ProfileId=profile.get('ProfileId')
        )
    """
    pass
