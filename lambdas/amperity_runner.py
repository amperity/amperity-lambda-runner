import ast

from datetime import datetime
from time import sleep

import requests


class AmperityRunner:
    def __init__(self, payload, lambda_context, destination_url, destination_session, 
                    batch_size=3500, batch_offset=0, rate_limit=None):
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
        """
        req = ast.literal_eval(payload)

        self.data_url = req.get('data_url')
        self.audience_data = req.get('settings', {})
        self.lambda_context = lambda_context
        self.destination_url = destination_url
        self.destination_session = destination_session

        self.batch_size = batch_size
        self.batch_offset = batch_offset
        self.rate_limit = rate_limit
        self.num_requests = 0
        self.rate_limit_time_start = None

        self.is_success = 200

    
    def start_job(self):
        print('starting job!')
        resp = requests.get(self.data_url)

        if resp.status_code != 200:
            print('Bad download')
            return resp.status_code

        file_content = resp.content.decode('utf-8').splitlines()

        print(f'Processing file from line: {self.batch_offset}')
        
        self._read_ndjson(file_content[self.batch_offset:])

    
    def _read_ndjson(self, file_content):
        file_length = len(file_content)

        # TODO: lambda timeout logic goes here
        while self.batch_offset < file_length:
            print('processing batch')

            batch = file_content[self.batch_offset: self.batch_offset + self.batch_size]
            # TODO: error handling? We should be able to trust the format of the file
            data_batch = [ast.literal_eval(d) for d in batch]

            print(data_batch)
            self.batch_offset += self.batch_size

            self._process_batch(data_batch)
            sleep(2)

            if self.lambda_context.get_remaining_time_in_millis() < 5000:
                print('Lambda timeout in less than 5 seconds. Ending job and kicking off another')

        return self.is_success


    def _process_batch(self, batch_data):
        # TODO: pull this out to a separate function. 
        output_data = [dict(d, **{
            'userId': d['cust_id'] if 'cust_id' in d else 1234,
            'audience_name': self.audience_data.get('audience_name'),
            'type': 'track',
            'event': 'Product Purchased'}) for d in batch_data]

        if not self.rate_limit_time_start:
            self.rate_limit_time_start = datetime.now()

        try:
            self._rate_limit()

            # NOTE: Do we want to always use json param or use data
            resp = self.destination_session.post(url=self.destination_url, json={'batch': output_data})
        except requests.RequestException as e:
            self.is_success = 400

            return self.is_success

        print(resp.status_code)
        print(resp.content)
        
        print(self.is_success)

    
    def _rate_limit(self):
        seconds_remaining = (datetime.now() - self.rate_limit_time_start).seconds

        if seconds_remaining <= 60 and self.num_requests > self.rate_limit:
            timeout = 60 - seconds_remaining

            print(f'Exceeded requests per minute. Sleeping: {timeout}')
            sleep(timeout)

        elif seconds_remaining > 60:
            self.rate_limit_time_start = datetime.now()
            self.num_requests = 0

        self.num_requests += 1
