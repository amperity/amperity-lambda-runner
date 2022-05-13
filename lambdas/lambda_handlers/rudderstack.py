import os

from amperity_runner import AmperityRunner

import requests


RS_APP_NAME=os.environ.get('RS_APP_NAME')
RS_WRITE_KEY=os.environ.get('RS_WRITE_KEY')


def lambda_handler(event, context):
    """
    Keep all lambda logic here. ie If timeout is about to be reached we should
        get a return value from `AmperityRunner` and kick off the next lambda with
        the updated offset

    :param event: Event object containing information about the invoking service
    :param context: Context object, passed to lambda at runtime, providing
                    information about the function and runtime environment
    """

    # This is how we know how long until the function times out.
    # https://docs.aws.amazon.com/lambda/latest/dg/python-context.html
    # print(context.get_remaining_time_in_millis())

    if not RS_APP_NAME or not RS_WRITE_KEY:
        print('Configure your environment variables plz :)')
        return

    destination_url = 'http://destination_app:5005/mock/rudderstack'
    sess = requests.Session()
    sess.auth = (RS_WRITE_KEY, '')
    sess.headers.update({'Content-Type': 'application/json'})

    runner = AmperityRunner(
        event['body'],
        context,
        destination_url,
        sess,
        batch_size=3,
        batch_offset=0,
        rate_limit=2
    )

    status = runner.start_job()

    if status == 'finished':
        # TODO test jsonify on response and include a message
        return { 'statusCode': 200 }
    elif status == 'timeout':
        print('Kicking off another lambda')
        return { 'statusCode': 300 }
    elif status == 'error':
        return { 'statusCode': 500 }
