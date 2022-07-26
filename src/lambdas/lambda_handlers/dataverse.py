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

def fetch_columns(single_table_name, access_token):
    headers = {
        "Accept": "application/json",
        "Content-type": "application/json; charset=utf-8",
        "Prefer": "return=representation",
        "Authorization": "Bearer " + access_token
        }

    url = f"https://{ORG_ID}.api.{ORG_REGION}.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='{single_table_name}')/Attributes"

    res = requests.get(url, headers=headers)

    if res.status_code == 200:
        items = res.json()
        values = items["value"]
        columns = set(map(lambda i: i["LogicalName"], values))

        return columns 

def dataverse_mapping(data, columns):
    return {k: data[k] for k in columns if k in data}

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

    table_name = "cr812_customers"
    destination_url = f"https://{ORG_ID}.api.{ORG_REGION}.dynamics.com/api/data/v9.2/{table_name}"

    amperity_runner = AmperityAPIRunner(payload, context, 'tenant-name', destination_url=None, destination_session=None)
    res = amperity_runner.run()

    return res