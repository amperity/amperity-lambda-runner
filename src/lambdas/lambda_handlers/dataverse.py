import json
import logging
import msal
import os
import requests
import uuid

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

def format_bulk_creation(batch_id, changeset_id, destination_url, data, cols):
    output = f"--batch_{batch_id}\n"
    output += f"Content-Type: multipart/mixed;boundary=changeset_{changeset_id}\n\n"
                
    for i, item in enumerate(data):
        formatted_item = {k: item[k] for k in cols if k in item}
        if not formatted_item:
            continue
        output += f"--changeset_{changeset_id}\n"
        output += "Content-Type: application/http\n"
        output += "Content-Transfer-Encoding: binary\n"
        output += "Content-ID: " + str(i) + "\n\n"
        output += f"POST {destination_url} HTTP/1.1\n"
        output += "Content-Type: application/json\n\n"
        output += str(formatted_item) + "\n\n"

    output += f"--changeset_{changeset_id}--\n"
    output += f"--batch_{batch_id}--"
    return output

def lambda_handler(event, context):
    print(event)
    payload = json.loads(event['body']) if type(event['body']) == str else event['body']
    access_token = authorize_msal()

    singular_table_name = "cr812_customer"
    plural_table_name = "cr812_customers"

    batch_url = f"https://{ORG_ID}.api.{ORG_REGION}.dynamics.com/api/data/v9.2/$batch"
    destination_url = f"https://{ORG_ID}.api.{ORG_REGION}.dynamics.com/api/data/v9.2/{plural_table_name}"    

    if not access_token:
        print("Unable to retrieve access token.")
        return

    sess = requests.Session()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Prefer": "return=representation",
        "Authorization": "Bearer " + access_token
        }
        
    sess.headers.update(headers)

    cols = fetch_columns(singular_table_name, sess)

    if not cols:
        return

    batch_id = str(uuid.uuid4())
    changeset_id = str(uuid.uuid4())
    sess.headers.update({"Content-Type": f"multipart/mixed;boundary=batch_{batch_id}"})

    def dataverse_mapping(data):
        return format_bulk_creation(batch_id, changeset_id, destination_url, data, cols)
    

    amperity_runner = AmperityAPIRunner(
        payload, 
        context, 
        'acme2-fullcdp-hackday', 
        destination_url=batch_url,
        destination_session=sess, 
        custom_mapping=dataverse_mapping
        )

    res = amperity_runner.run()

    return res
    
"""
curl -X POST 'http://localhost:5555/lambda/dataverse' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/dataverse.ndjson", "callback_url": "http://api_destination:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'    
"""    