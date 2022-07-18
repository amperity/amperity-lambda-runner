import functools, json

from datetime import datetime
from time import sleep

import boto3
import requests


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
        # if self.lambda_context.get_remaining_time_in_millis() < 5000:
        #     print('Lambda timeout in less than 5 seconds.')
        #     resp = boto3.client('lambda').invoke(
        # Can function name become a param from context
        #         FunctionName='phil-test',
        #         InvocationType='Event',
        #         Payload=json.dumps({'chain_lambda': False}))

        #     if resp.get('StatusCode') == 202:
        #         return 'timeout'
        #     else:
        #         return 'error'

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


class AmperityRunner:
    def __init__(self, payload, lambda_context, tenant_id, batch_size=2000, batch_offset=0):
        """
        :params
            payload : str
                The body of the lambda event object
                payload = {
                    "data_url": "", 
                    "settings": {},
                    "callback_url": "",
                    "webhook_id": "",
                    "access_token": ""
                }
            context : LambdaContext
                The context object provided by lambda
            batch_size : int, optional
                Int representing how many records should go in a single outbound request
            batch_offset : int, optional
                If a single job cannot process all records this represents where the next job should pickup
        """
        self.lambda_context = lambda_context
        self.batch_size = batch_size
        self.batch_offset = batch_offset

        self.tenant_id = tenant_id

        self.data_url = payload.get('data_url')
        self.settings = payload.get('settings')
        self.access_token = payload.get('access_token')

        self.status_url = payload.get('callback_url') + payload.get('webhook_id')
        self.callback_session = requests.Session()
        self.callback_session.headers.update({
            'Content-Type': 'application/json',
            'X-Amperity-Tenant': self.tenant_id,
            'Authorization': f'Bearer {self.access_token}'
        })


    def poll_for_status(self, state, progress=0, errors=[], reason=''):
        data = json.dumps({
            'state': state,
            'progress': progress,
            'errors': errors,
            'reason': reason
        })
        res = self.callback_session.put(self.status_url, data=data)

        print('Polling for status...', data, res)

        return res


    def runner_logic(self):
        pass


    def run(self):
        errors = []

        start_response = self.poll_for_status('running', 0, errors)

        # Do we want to kill a lambda if it can't report status to the app?
        if start_response.status_code != 200:
            return http_response(start_response.status_code, 'ERROR', 'Error polling for status.')

        with requests.get(self.data_url, stream=True) as resp:
            if resp.status_code != 200:
                self.poll_for_status('failed', 0, errors=[], reason='Failed to download file.')

                return resp

            data_batch = []

            for i, row in enumerate(resp.iter_lines(decode_unicode=True)):
                # batch_offset should persist (be passed) b/w lambda runs if a timeout occurs.
                # We cannot stream to an offset so skip iterations while we are catching up.
                if i <= self.batch_offset:
                    continue

                data = json.loads(row)

                if len(data_batch) <= self.batch_size:
                    data_batch.append(data)
                else:
                    self.runner_logic(data_batch)
                    data_batch = [data]
                    self.batch_offset += self.batch_size
                    # TODO - need to track offset as a percentage
                    self.poll_for_status('running', .5, errors)

                print(len(data_batch))

        if len(data_batch) > 0:
            self.runner_logic(data_batch)

        end_poll_response = self.poll_for_status('succeeded', 1, errors)

        # TODO - We should return more than just the request object from poll_for_status
        return end_poll_response


class AmperityAPIRunner(AmperityRunner):
    def __init__(self, *args, destination_url=None, destination_session=None, rate_limit=None, custom_mapping=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.destination_url = destination_url
        self.destination_session = destination_session
        self.rate_limit = rate_limit
        self.num_requests = 0
        self.rate_limit_time_start = None
        self.custom_mapping = custom_mapping

    @rate_limit
    def runner_logic(self, data):
        if self.custom_mapping:
            output_data = [self.custom_mapping(d) for d in data]

        resp = self.destination_session.post(
            url=self.destination_url,
            data=json.dumps({'batch': output_data if output_data else data})
        )

        if resp.status_code != 200:
            print('POST failed: ')
            print(resp.content)


class AmperityBotoRunner(AmperityRunner):
    def __init__(self, *args, boto_client=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not boto_client:
            raise NotImplementedError('Please supply a valid boto client')

        self.boto_client = boto_client


    def runner_logic(self, data):
        raise NotImplementedError('Please implement your boto runnder logic.')

