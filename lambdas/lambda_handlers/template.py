import json

from amperity_runner import AmperityRunner
from response import http_response

def main(data):
    # DO STUFF
    return http_response(200, "SUCCESS", "Successfully ran function")

def lambda_handler(event, context):
    print(event)
    payload = json.loads(event["body"])
    amperity = AmperityRunner(payload = payload, lambda_context = context, read_as_ndjson = True)
    res = amperity.run(main)
   
    return res