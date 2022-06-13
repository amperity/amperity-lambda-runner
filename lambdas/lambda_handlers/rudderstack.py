import os, json

from amperity_runner import AmperityRunner

import requests

# TODO: These shouldn't be defined in the compose file. Need an easier way to configure env variables
RS_APP_NAME=os.environ.get('RS_APP_NAME')
RS_WRITE_KEY=os.environ.get('RS_WRITE_KEY')


def lambda_handler(event, context):
    """
    :param event: Event object containing information about the invoking service
    :param context: Context object, passed to lambda at runtime, providing
                    information about the function and runtime environment
    """

    if not RS_APP_NAME or not RS_WRITE_KEY:
        print('Configure your environment variables plz :)')
        return

    destination_url = 'http://destination_app:5005/mock/rudderstack'
    sess = requests.Session()
    sess.auth = (RS_WRITE_KEY, '')
    sess.headers.update({'Content-Type': 'application/json'})

    payload = json.loads(event['body'])

    add_customer_id = lambda d: dict(d, **{
            'userId': d['cust_id'] if 'cust_id' in d else 1234,
            'audience_name': payload.get('audience_name'),
            'type': 'track',
            'event': 'Product Purchased'})

    runner = AmperityRunner(
        payload,
        context,
        destination_url,
        sess,
        # batch_size=3500,
        # batch_offset=0,
        # rate_limit=10000,
        custom_mapping=add_customer_id,
    )

    status = runner.start_job()

    if status == 'finished':
        return { 'statusCode': 200 }
    elif status == 'timeout':
        print('Kicking off another lambda')
        return { 'statusCode': 300 }
    else:
        return { 'statusCode': 500 }
