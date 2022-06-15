import functools, json, requests
from datetime import datetime
from time import sleep

from response import http_response

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
    def __init__(self, payload, lambda_context, batch_size=3500, batch_offset=0, rate_limit=None, custom_mapping=None, read_as_ndjson=False):
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
        self.batch_size = batch_size
        self.batch_offset = batch_offset
        self.rate_limit = rate_limit
        self.num_requests = 0
        self.rate_limit_time_start = None
        self.custom_mapping = custom_mapping
        self.read_as_ndjson = read_as_ndjson

        self.tenant_id = payload.get("tenant_id")

        self.data_url = payload.get("data_url")
        self.webhook_settings = payload.get("webhook_settings")
        self.callback_url = payload.get("callback_url")
        self.webhook_id = payload.get("webhook_id")
        self.access_token = payload.get("access_token")

        self.status_url = self.callback_url + self.webhook_id
    
    def download_file(self, url):
        print("Downloading file...", url)
        res = requests.get(url)

        return res
    
    def poll_for_status(self, state, progress=0, errors=[]):
        headers = {
            'Content-Type': 'application/json',
            'X-Amperity-Tenant': self.tenant_id,
            'Authorization': f'Bearer {self.access_token}'
            }
        data = json.dumps({
            "state": state,
            "progress": progress,
            "errors": errors})
        res = requests.put(self.status_url, headers=headers, data=data)
        print("Polling for status...", headers, data, res)

        return res
    
    def read_ndjson(self, data, batch_offset, batch_size):
        """
        The thought here is to allow the user to set
        whether or not they read the NDJSON within the run function.
        Some users may want to process the entire file instead of splitting into batches.

        Is the idea here to actually batch because we're afraid of Lambda timing out? 
        If we're afraid of Lambda timing out, does this mean we need to trigger another Lambda to run?
        """
        print("Reading NDJSON...")
        data_array = data.decode('utf-8').splitlines()
        batch = data_array[self.batch_offset: self.batch_offset + self.batch_size]
        data_batch = [json.loads(d) for d in batch]

        return data_batch
    
    @rate_limit
    def run(self, callback):
        errors = []

        start_response = self.poll_for_status("running", 0, errors)

        if start_response.status_code != 200:

            return http_response(start_response.status_code, "ERROR", "Error polling for status.")

        downloaded_file = self.download_file(self.data_url)

        if downloaded_file.status_code != 200:
            errors.append("Failed to download file...")
            download_failed_poll_response = self.poll_for_status("failed", 0, errors)

            if download_failed_poll_response.status_code != 200:

                return download_failed_poll_response

            return http_response(res.status_code, "ERROR", "Error downloading file.")
        
        if self.read_as_ndjson == True:
            data_batch = self.read_ndjson(downloaded_file.content, self.batch_offset, self.batch_size)
            res = callback(data_batch)

        else:
            res = callback(downloaded_file.content)
        
        if res["statusCode"] != 200:
            errors.append(res["body"])
            end_error_poll_response = self.poll_for_status("failed", 0, errors)

            if end_error_poll_response.status_code != 200:

                return http_response(end_error_poll_response.status_code, "ERROR", "Error polling for status.")

            return res

        end_poll_response = self.poll_for_status("succeeded", 1, errors)

        if end_poll_response.status_code != 200:

            return http_response(end_poll_response.status_code, "ERROR", "Error polling for status.")

        return res