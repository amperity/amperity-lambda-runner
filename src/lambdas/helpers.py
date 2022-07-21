import functools
import json

from datetime import datetime
from time import sleep

import boto3


def http_response(status_code, status, message):
    body = {
        "status": status,
        "message": message
    }

    return {
        "statusCode": status_code,
        "body": json.dumps(body)
    }


def rate_limit(f):
    """
    Decorator to handle our rate-limit/lambda timeout logic.
    First we check for the lambda_context timeout. Depending we either end this job 
        and kick off another lambda or continue to our post request to the destination api.
    In the destination request we keep track of requests per minute. If we exceed 
        the requests allowed per minute we pause the remaining time in the minute.
    """
    @functools.wraps(f)
    def rate_limit_wrapper(self, *args, **kwargs):
        """
        The logic works for invoking another lambda but leaving it out until we actually need to implement it.
        Right now when we invoke using boto3 client we get a different datatype (dict) which breaks our parsing logic.
        Either we write better parsing logic or we re-invoke the lambda using the API gateway which seems...messy
        """
        if self.lambda_context.get_remaining_time_in_millis() < 5000:
            print('Lambda timeout in less than 5 seconds.')

            resp = boto3.client('lambda').invoke(
                FunctionName=self.lambda_context.function_name,
                InvocationType='Event',
                # NOTE this invokes the lambda directly NOT through the HTTP gateway. Meaning the datatype
                #   coming into the next lambda is a dict not str.
                Payload=json.dumps({
                    'batch_offset': self.batch_offset,
                    'data_url': self.data_url,
                    'etc': 'the whole event payload (could we do **self)'
                }))

            if resp.get('StatusCode') == 202:
                return 'timeout'
            else:
                return 'error'

        if not self.rate_limit:
            return f(self, *args, **kwargs)

        if not self.rate_limit_time_start:
            self.rate_limit_time_start = datetime.now()

        seconds_remaining = (datetime.now() - self.rate_limit_time_start).seconds

        if seconds_remaining <= 60 and self.num_requests > self.rate_limit:
            timeout = 60 - seconds_remaining

            print(f'Exceeded requests per minute. Sleeping: {timeout}')
            sleep(timeout)

        elif seconds_remaining > 60:
            self.rate_limit_time_start = datetime.now()
            self.num_requests = 0

        # NOTE: Do we want to count number or requests sent or number of records sent
        self.num_requests += 1

        return f(self, *args, **kwargs)

    return rate_limit_wrapper