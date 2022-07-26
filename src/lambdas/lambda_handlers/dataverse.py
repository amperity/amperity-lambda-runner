import json
import logging
import msal
import os
import requests

from lambdas.amperity_runner import AmperityAPIRunner

ORG_ID = os.getenv("ORG_ID")
ORG_REGION = os.getenv("ORG_REGION")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

AUTHORITY = "https://login.microsoftonline.com/" + TENANT_ID
SCOPE = [f"https://{ORG_ID}.api.{ORG_REGION}.dynamics.com/.default"]

def authorize_msal():
    # https://github.com/AzureAD/microsoft-authentication-library-for-python/blob/dev/sample/confidential_client_secret_sample.py
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = None

    result = app.acquire_token_silent(SCOPE, account=None)

    if not result:
        logging.info("No suitable token exists in cache. Let's get a new one from AAD.")
        result = app.acquire_token_for_client(scopes=SCOPE)
    
    access_token = result.get("access_token")

    return access_token

def fetch_columns(single_table_name, session):

    url = f"https://{ORG_ID}.api.{ORG_REGION}.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='{single_table_name}')/Attributes"

    res = session.get(url)

    if res.status_code == 200:
        items = res.json()
        values = items["value"]
        columns = set(map(lambda i: i["LogicalName"], values))

        return columns 

def lambda_handler(event, context):
    print(event)
    payload = json.loads(event['body']) if type(event['body']) == str else event['body']
    access_token = authorize_msal()

    if not access_token:
        print("Unable to retrieve access token.")
        return

    sess = requests.Session()
    headers = {
        "Accept": "application/json",
        "Content-type": "application/json; charset=utf-8",
        "Prefer": "return=representation",
        "Authorization": "Bearer " + access_token
        }
        
    sess.headers.update(headers)

    cols = fetch_columns("cr812_customer", sess)
    print(cols)

    def dataverse_mapping(data):
        # Removes columns from the data that don't exist in the schema
        return {k: data[k] for k in cols if k in data}

    table_name = "cr812_customers"
    destination_url = f"https://{ORG_ID}.api.{ORG_REGION}.dynamics.com/api/data/v9.2/{table_name}"

    amperity_runner = AmperityAPIRunner(
        payload, 
        context, 
        'acme2-fullcdp-hackday', 
        destination_url=destination_url, 
        destination_session=sess, 
        custom_mapping=dataverse_mapping
        )

    res = amperity_runner.run()

    return res

# curl -X POST 'http://localhost:5555/lambda/dataverse' \
#     -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/dataverse.ndjson", "callback_url": "http://api_destination:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'    