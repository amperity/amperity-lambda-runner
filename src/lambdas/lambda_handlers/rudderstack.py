import json
import os

from lambdas.amperity_runner import AmperityAPIRunner

import requests


RS_APP_NAME = os.environ.get('RS_APP_NAME', 'fake_app')
RS_WRITE_KEY = os.environ.get('RS_WRITE_KEY', 'fake_key')


def lambda_handler(event, context):
    """
    :param event: Event object containing information about the invoking service
    :param context: Context object, passed to lambda at runtime, providing
                    information about the function and runtime environment
    """

    if not RS_APP_NAME or not RS_WRITE_KEY:
        print('Configure your environment variables plz :)')
        return

    destination_url = 'http://api_destination:5005/mock/rudderstack'
    sess = requests.Session()
    sess.auth = (RS_WRITE_KEY, '')
    sess.headers.update({'Content-Type': 'application/json'})

    payload = json.loads(event['body'])

    def add_customer_id(d):
        return dict(d, **{
            'userId': d['cust_id'] if 'cust_id' in d else 1234,
            'audience_name': payload.get('audience_name'),
            'type': 'track',
            'event': 'Product Purchased'
        })

    runner = AmperityAPIRunner(
        payload,
        context,
        'test',
        batch_size=5,
        batch_offset=0,
        destination_url=destination_url,
        destination_session=sess,
        custom_mapping=add_customer_id,
        data_key='batch',
    )

    status = runner.run()

    return status
