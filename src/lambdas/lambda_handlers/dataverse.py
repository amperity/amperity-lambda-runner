import json
import logging
import msal
import os
import requests
import uuid

from lambdas.amperity_runner import AmperityAPIRunner

PA_ENV_NAME = os.getenv("PA_ENV_NAME")
PA_ENV_REGION = os.getenv("PA_ENV_REGION")
AZ_TENANT_ID = os.getenv("AZ_TENANT_ID")
AZ_CLIENT_ID = os.getenv("AZ_CLIENT_ID")
AZ_CLIENT_SECRET = os.getenv("AZ_CLIENT_SECRET")

SINGULAR_TABLE_NAME = os.getenv("SINGULAR_TABLE_NAME")
PLURAL_TABLE_NAME = os.getenv("PLURAL_TABLE_NAME")

AUTHORITY = "https://login.microsoftonline.com/" + AZ_TENANT_ID
SCOPE = [f"https://{PA_ENV_NAME}.api.{PA_ENV_REGION}.dynamics.com/.default"]


def authorize_msal():
    # https://github.com/AzureAD/microsoft-authentication-library-for-python/blob/dev/sample/confidential_client_secret_sample.py
    app = msal.ConfidentialClientApplication(AZ_CLIENT_ID, authority=AUTHORITY, client_credential=AZ_CLIENT_SECRET)
    result = None

    result = app.acquire_token_silent(SCOPE, account=None)

    if not result:
        logging.info("No suitable token exists in cache. Let's get a new one from AAD.")
        result = app.acquire_token_for_client(scopes=SCOPE)

    access_token = result.get("access_token")

    return access_token


def fetch_columns(single_table_name, session):

    url = f"https://{PA_ENV_NAME}.api.{PA_ENV_REGION}.dynamics.com/api/data/v9.2/EntityDefinitions(LogicalName='{single_table_name}')/Attributes"

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
    amperity_tenant_id = payload.get("tenant_id")

    access_token = authorize_msal()

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

    cols = fetch_columns(SINGULAR_TABLE_NAME, sess)

    if not cols:
        return

    batch_id = str(uuid.uuid4())
    changeset_id = str(uuid.uuid4())
    sess.headers.update({"Content-Type": f"multipart/mixed;boundary=batch_{batch_id}"})

    batch_url = f"https://{PA_ENV_NAME}.api.{PA_ENV_REGION}.dynamics.com/api/data/v9.2/$batch"
    destination_url = f"https://{PA_ENV_NAME}.api.{PA_ENV_REGION}.dynamics.com/api/data/v9.2/{PLURAL_TABLE_NAME}"

    def dataverse_mapping(data):
        return format_bulk_creation(batch_id, changeset_id, destination_url, data, cols)

    amperity_runner = AmperityAPIRunner(
        payload,
        context,
        amperity_tenant_id,
        destination_url=batch_url,
        destination_session=sess,
        custom_mapping=dataverse_mapping
        )

    res = amperity_runner.run()

    return res
