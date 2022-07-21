import os, json

from datetime import datetime
from importlib import import_module

from dotenv import load_dotenv
from flask import Flask, request, jsonify


load_dotenv()


app = Flask(__name__)


TIMEOUT=os.environ.get('LAMBDA_TIMEOUT')


class LambdaContext:
    """
    A mock lambda context instance. See link for full capabilities in a lambda.
    https://docs.aws.amazon.com/lambda/latest/dg/python-context.html
    """
    def __init__(self):
        print(os.environ.get('LAMBDA_TIMEOUT'))
        self.start = datetime.now()
        self.timeout = int(TIMEOUT) if TIMEOUT else (1 * 60 * 1000)
        self.function_name = 'fake_function_name'

    def get_remaining_time_in_millis(self):
        return self.timeout - ((datetime.now() - self.start).seconds * 1000)


@app.route('/health')
def health_check():
    print('Checking Health')
    return jsonify(message="up", status=200)


"""
Example simple curl:
curl -X POST 'http://localhost:5555/lambda/rudderstack' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/sample.ndjson"}'

Example full curl:
curl -X POST 'http://localhost:5555/lambda/rudderstack' \
    -H 'Content-Type: application/json' \
    -d '{ "label_name": "test label", "webhook_settings": {"mock":"data"}, "access_token": "some-token", "webhook_id": "some-id", "callback_url": "https://app.amperity.systems/api/v1/plugin/webhook/", "data_url": "http://fake_s3:4566/test-bucket/sample.ndjson" }'
"""
@app.route("/lambda/<name>", methods=["POST"])
def mock_lambda(name):
    print(f'Testing lambda: {name}')
    # NOTE: actual lambda gateway does NOT parse json body for us
    req = request.json
    context = LambdaContext()
    event = {'body': json.dumps(req)}

    lambda_module = import_module(f'lambda_handlers.{name}')
    lambda_status = lambda_module.lambda_handler(event, context)

    return jsonify(status=lambda_status.status_code)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5555)
