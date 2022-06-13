import requests
import sys
sys.path.append("../")
from amperity_runner import AmperityRunner


def main_function(data, errors, url, args):
    print("main_function data", data)
    print("main_function args", args)
    # res = requests.get(url)
    print("errors from main_function", errors)

def lambda_handler(event, context):
    url = event["data_url"]
    amperity = AmperityRunner(payload = event, lambda_context = context, read_ndjson = False)
    amperity.run(main_function, url, "hi")

payload = {
    "data_url": "https://www.google.com",
    "webhook_settings": {},
    "callback_url": "https://www.google.com/",
    "webhook_id": "webhook_id",
    "access_token": "access_token"
    }
lambda_context = {"context": "hi"}

lambda_handler(payload, lambda_context)