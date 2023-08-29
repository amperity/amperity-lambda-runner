import json
import logging

from lambdas.amperity_runner import AmperityAPIRunner

import requests


def lambda_handler(event, context):
    """
    Bare bones lambda runner demo.
    Start from here if you're messing around with local.
    """
    logging.info(event)
    payload = json.loads(event['body'])

    destination_url = 'http://api_destination:5005/mock/destination'
    destination_url = 'http://api_destination:5005/mock/error/502'
    sess = requests.Session()
    sess.auth = ('', '')
    sess.headers.update({'Content-Type': 'application/json'})

    amperity_runner = AmperityAPIRunner(
        payload,
        context,
        'tenant-name',
        destination_url=destination_url,
        destination_session=sess,
    )
    res = amperity_runner.run()
    logging.info('Lambda executed successfully')

    return res
