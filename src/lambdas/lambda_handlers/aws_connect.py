import json

import boto3

from lambdas.amperity_runner import AmperityBotoRunner

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
CONNECT_DOMAIN = 'amazon-connect-amperity-acme'
CONNECT_CLIENT = boto3.client(
    'customer-profiles',
    region_name='us-east-1',
)


class AmperityConnectRunner(AmperityBotoRunner):
    """
    Example of how to use the BotoRunner and the parent of a custom Boto class. Another approach would be to write
    your own callback function and override runner_logic in your class instance.
    (ie connect_runner.runner_logic = callback)
    Currently not super opinionated on which approach you take.

    This implementation is inefficient b/c runner_logic is invoked with a list of records. Then we parse each record
    individually again. Not a huge deal for a demo but if this ever needs to go to prod we should rewrite.

    """
    def runner_logic(self, data):
        address_dict = {
            'address': 'Address1',
            'city': 'City',
            'state': 'State',
            'postal': 'PostalCode',
            'country': 'Country'
        }

        for record in data:
            print(record)
            address_val = {}
            row_val = {}

            for key, val in record.items():
                # Connect doesn't support NoneTypes skip any missing values
                if not val:
                    continue

                if key in address_dict:
                    address_val[address_dict[key]] = val
                else:
                    row_val[key] = val

            row_val['Address'] = address_val

            CONNECT_CLIENT.create_profile(
                DomainName=CONNECT_DOMAIN,
                PartyType='INDIVIDUAL',
                **row_val
            )


def lambda_handler(event, context):
    payload = json.loads(event['body'])

    connect_runner = AmperityConnectRunner(
        payload,
        context,
        'test',
        boto_client=CONNECT_CLIENT
    )

    status = connect_runner.run()

    return status
