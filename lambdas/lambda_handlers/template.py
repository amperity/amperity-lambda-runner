import json

from amperity_runner import AmperityRunner, http_response

def main(data):
    # DO STUFF
    return http_response(200, "SUCCESS", "Successfully ran function")

def lambda_handler(event, context):
    print(event)
    payload = json.loads(event["body"])
    payload["tenant_id"] = 'acme2-fullcdp-hackday' # this will be added into the payload
    amperity = AmperityRunner(payload=payload, lambda_context=context, read_as_ndjson=True)
    res = amperity.run(main)
   
    return res
