import json
import logging

from lambdas.amperity_runner import AmperityAPIRunner


def lambda_handler(event, context):
    """
    Bare bones lambda runner template.
    Start from here if you're developing your own lambda.
    """
    logging.info(event)
    payload = json.loads(event['body'])

    amperity_runner = AmperityAPIRunner(
        payload,
        context,
        'tenant-name'
    )
    res = amperity_runner.run()
    logging.info('Lambda executed successfully')

    return res
