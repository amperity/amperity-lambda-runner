import json
import os

from datetime import datetime
from importlib import import_module

from dotenv import load_dotenv
from flask import Flask, request, jsonify


load_dotenv()


app = Flask(__name__)


TIMEOUT = os.environ.get('LAMBDA_TIMEOUT')


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


@app.route("/lambda/<name>", methods=["POST"])
def mock_lambda(name):
    print(f'Testing lambda: {name}')
    # NOTE - actual lambda gateway does NOT parse json body for us
    req = request.json
    context = LambdaContext()
    event = {'body': json.dumps(req)}

    lambda_module = import_module(f'lambdas.lambda_handlers.{name}')
    lambda_status = lambda_module.lambda_handler(event, context)

    return jsonify(status=lambda_status.get('statusCode'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5555)
