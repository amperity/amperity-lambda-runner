import json

from lambdas.amperity_runner import AmperityAPIRunner


def lambda_handler(event, context):
    print(event)
    payload = json.loads(event['body']) if type(event['body']) == str else event['body']

    amperity_runner = AmperityAPIRunner(
        payload,
        context,
        'tenant-name'
    )
    res = amperity_runner.run()

    return res
