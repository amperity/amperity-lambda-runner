import json
import requests
from response import http_response

class AmperityRunner:
    def __init__(self, payload, lambda_context, batch_size=3500, batch_offset=0, rate_limit=None, custom_mapping=None, read_as_ndjson = False):
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

        # TODO: Add Tenant ID to payload
        self.tenant_id = 'acme2-fullcdp-hackday'

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
    
    def poll_for_status(self, state, progress = 0, errors = []):
        headers = {
            'Content-Type': 'application/json',
            'X-Amperity-Tenant': self.tenant_id,
            'Authorization': f'Bearer {self.access_token}'
            }
        data = json.dumps({
            "state": state,
            "progress": progress,
            "errors": errors})
        res = requests.put(self.status_url, headers = headers, data = data)
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
    
    def run(self, callback):
        errors = []

        start_response = self.poll_for_status("running", 0, errors)
        if start_response.status_code != 200:
            return http_response(start_response.status_code, "ERROR", "Error polling for status.")

        downloaded_file = self.download_file(self.data_url)
        if downloaded_file.status_code != 200:
            errors.append(downloaded_file["body"])
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