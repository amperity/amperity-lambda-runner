import os, json

from datetime import datetime

from flask import Flask, request, jsonify

# TODO how to import all modules under folder
from lambda_handlers.rudderstack import lambda_handler


app = Flask(__name__)


TIMEOUT=os.environ.get('LAMBDA_TIMEOUT')


class LambdaContext:
    def __init__(self):
        self.start = datetime.now()
        self.timeout = TIMEOUT if TIMEOUT else 5000

    def get_remaining_time_in_millis(self):
        return self.timeout - ((datetime.now() - self.start).seconds * 1000)


@app.route('/health')
def health_check():
    print('Checking Health')
    return jsonify(message="up", status=200)


"""
curl -X POST 'http://localhost:5555/lambda/rudderstack' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/example.ndjson"}'


TODO:
1) register lambda "runners" under a unique name
2) Pass that name as a param to the test route
3) Run that lambda while testing
"""
@app.route("/lambda/<name>", methods=["POST"])
def mock_lambda(name):
    # TODO: ideally this finds the specific lambda handler to test
    print(f'Testing lambda: {name}')
    # NOTE: actual lambda gateway does NOT parse json body for us...I think
    req = request.json
    context = LambdaContext()
    # TODO need to confirm the exact type of what comes into a lambda
    event = {'body': json.dumps(req)}
    lambda_handler(event, context)

    return jsonify(status=200)


if __name__ == '__main__':
    dummy_gateway_event = {
        "body": """{
            "settings": {
                "audience_name": "Test Audience",
            },
            "webhook_url": "https://app.amperity.com/plugin/...",
            "access_token": "top_secret",
            "data_url": "",
        }"""
    }

    # lambda_handler(dummy_gateway_event, {})

    app.run(debug=True, host='0.0.0.0', port=5555)
