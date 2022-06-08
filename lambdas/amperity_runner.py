import functools ,json

from datetime import datetime
from time import sleep

import boto3
import requests


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
    def __init__(self, payload, lambda_context, destination_url, destination_session, 
                    batch_size=3500, batch_offset=0, rate_limit=None, custom_mapping=None):
        """
        :params
            payload : str
                The body of the lambda event object
            context : LambdaContext
                The context object provided by lambda
            destination_url : str
                The url to send the data to
            destination_session : requests.Session
                An instance of a requests.Session class with all authorization configured.
            batch_size : int, optional
                Int representing how many records should go in a single outbound request
            batch_offset : int, optional
                If a single job cannot process all records this represents where the next job should pickup
            rate_limit : int, optional
                Integer denoting the requests per minute allowed by the destination.
            custom_mapping : lambda, optional
                Lambda function that does some operation on the shape of the data.
        """
        self.data_url = payload.get('data_url')
        self.audience_data = payload.get('webhook_settings', {})
        callback_url = payload.get('callback_url')
        webhook_id = payload.get('webhook_id')

        self.status_url = callback_url + webhook_id
        self.access_token = payload.get('access_token')

        self.lambda_context = lambda_context

        self.destination_url = destination_url
        self.destination_session = destination_session

        self.batch_size = batch_size
        self.batch_offset = batch_offset
        self.rate_limit = rate_limit
        self.num_requests = 0
        self.rate_limit_time_start = None
        self.custom_mapping = custom_mapping

    
    def start_job(self):
        resp = requests.get(self.data_url)

        if resp.status_code != 200:
            print('Bad download')
            return 'error'

        file_content = resp.content.decode('utf-8').splitlines()

        print(f'Processing file from line: {self.batch_offset}')
        
        job_status = self._read_ndjson(file_content[self.batch_offset:])

        # self._update_status()

        return job_status

    
    def _read_ndjson(self, file_content):
        file_length = len(file_content)

        # TODO: lambda timeout logic goes here
        while self.batch_offset < file_length:
            batch = file_content[self.batch_offset: self.batch_offset + self.batch_size]
            # TODO: error handling? We should be able to trust the format of the file...we write it
            data_batch = [json.loads(d) for d in batch]

            self.batch_offset += len(data_batch) if len(data_batch) < self.batch_size else self.batch_size

            # TODO: Reporting status to the callback url. How often do we want to do that?
            batch_status = self._process_batch(data_batch)

            print(f'Finished processing {self.batch_offset} records')

            if batch_status == 'timeout':
                return batch_status

        return 'success'


    @rate_limit
    def _process_batch(self, batch_data):
        if self.custom_mapping:
            output_data = [self.custom_mapping(d) for d in batch_data]

        resp = self.destination_session.post(url=self.destination_url, data=json.dumps({'batch': output_data if output_data else batch_data}))

        if resp.status_code != 200:
            print('POST failed: ')
            print(resp.content)


    def _update_status(self):
        """
        Testing this locally is blocked by docker networking for now. Use the below curl on local
        curl -X PUT 'http://app.local.amperity.systems:8093/webhook/v1/< webhook-id >' \
            -H 'X-Amperity-Tenant: planex' \
            -H 'Authorization: Bearer < access-token >' \
            -H 'Content-Type: application/json' -d '{"status": "succeeded"}'

        TODO: Remove hardcoded payload for data passed in from params
        """

        resp = requests.put(
            self.status_url,
            headers={
                'Content-Type': 'application/json',
                'X-Amperity-Tenant': 'noodles',
                'Authorization': f'Bearer {self.access_token}'
            }, 
            data=json.dumps({
                "state": "succeeded",
                "progress": 1,
                "errors": ["no errors ever :)"]}))
        print(resp)
