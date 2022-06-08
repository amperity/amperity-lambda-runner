import os, json

from amperity_runner import AmperityRunner

import requests

# TODO: These shouldn't be defined in the compose file. Need an easier way to configure env variables
SOME_ENV_VAR=os.environ.get('SOME_ENV_VAR')


def lambda_handler(event, context):
    """
    :param event: Event object containing information about the invoking service
    :param context: Context object, passed to lambda at runtime, providing
                    information about the function and runtime environment
    """

    if not SOME_ENV_VAR:
        print('Configure your environment variables plz :)')
        return

    # Configure your session to your destination requirements here.
    destination_url = 'http://destination_app:5005/mock/rudderstack'
    sess = requests.Session()
    sess.auth = (SOME_ENV_VAR, '')
    sess.headers.update({'Content-Type': 'application/json'})

    req = event['body']
    payload = json.loads(req)

    # There are more fields to configure for batch sizing, rate limiting, etc.
    #   See amperity_runner.py if you want to override any of those values
    runner = AmperityRunner(
        payload,
        context,
        destination_url,
        sess,
    )

    status = runner.start_job()

    if status == 'finished':
        return { 'statusCode': 200 }
    elif status == 'timeout':
        print('Kicking off another lambda')
        return { 'statusCode': 300 }
    else:
        return { 'statusCode': 500 }
