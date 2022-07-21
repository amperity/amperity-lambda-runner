import json

from amperity_runner import AmperityAPIRunner, http_response


"""
curl -X POST 'http://localhost:5555/lambda/template' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/sample.ndjson", "callback_url": "http://destination_app:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'
"""


def lambda_handler(event, context):
    print(event)
    payload = json.loads(event["body"])

    amperity_runner = AmperityAPIRunner(
        payload,
        context,
        'tenant-name'
    )
    res = amperity_runner.run()

    return res
