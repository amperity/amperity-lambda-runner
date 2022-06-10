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
                payload = {
                    "data_url": "", 
                    "webhook_settings": {},
                    "callback_url": "",
                    "webhook_id": "",
                    "access_token": ""
                    }
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

        self.lambda_context = lambda_context
        self.destination_url = destination_url
        self.destination_session = destination_session
        self.batch_size = batch_size
        self.batch_offset = batch_offset
        self.rate_limit = rate_limit
        self.num_requests = 0
        self.rate_limit_time_start = None
        self.custom_mapping = custom_mapping

        self.data_url = self.payload.get("data_url")
        self.webhook_settings = self.payload.get("webhook_settings")
        self.callback_url = self.payload.get("callback_url")
        self.webhook_id = self.payload.get("webhook_id")
        self.access_token = self.payload.get("access_token")

        self.status_url = self.callback_url + self.webhook_id

    
    def download_file(self, url):
        res = requests.get(url)
        if res.status_code != 200:
            print("Could not download file.")
            return False
        return res.content
    
    def poll_for_status(self, state, progress = 0, errors = []):
        headers = {
            'Content-Type': 'application/json',
            'X-Amperity-Tenant': 'noodles',
            'Authorization': f'Bearer {self.access_token}'
            }
        data = json.dumps({
            "state": state,
            "progress": progress,
            "errors": errors})
        res = requests.put(self.status_url, headers = headers, data = data)
        print(res)
        # add some error handling, or handle this response somehow?
    
    def run(self, callback):
        errors = []
        self.poll_for_status("running", 0, errors)
        downloaded_file = self.download_file(self.data_url)
        if not downloaded_file:
            errors.append("Could not download file.")
            self.poll_for_status("failed", 0, errors)
            return False

        res = callback(errors)
        if not res:
            errors.append("Error running function.")
            self.poll_for_status("failed", 0, errors)
            return False
        self.poll_for_status("succeeded", 1, errors)