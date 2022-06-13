import json
import requests

class AmperityRunner:
    def __init__(self, payload, lambda_context, batch_size=3500, batch_offset=0, rate_limit=None, custom_mapping=None, read_ndjson = False):
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
        self.batch_size = batch_size
        self.batch_offset = batch_offset
        self.rate_limit = rate_limit
        self.num_requests = 0
        self.rate_limit_time_start = None
        self.custom_mapping = custom_mapping

        self.data_url = payload.get("data_url")
        self.webhook_settings = payload.get("webhook_settings")
        self.callback_url = payload.get("callback_url")
        self.webhook_id = payload.get("webhook_id")
        self.access_token = payload.get("access_token")

        self.status_url = self.callback_url + self.webhook_id
    
    def download_file(self, url):
        print("Downloading file.")
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
        print("poll for status", res)
        # add some error handling, or handle this response somehow?
    
    def read_ndjson(self, data, batch_offset, batch_size):
        """
        The thought here is to allow the user to set
        whether or not they read the NDJSON within the run function.

        Some users may want to process the entire file instead of splitting
        into batches.
        """
        data_array = data.decode('utf-8').splitlines()
        batch = data_array[self.batch_offset: self.batch_offset + self.batch_size]
        data_batch = [json.loads(d) for d in batch]
        return data_batch
    
    def run(self, callback, *args):
        errors = []
        self.poll_for_status("running", 0, errors)
        downloaded_file = self.download_file(self.data_url)
        if not downloaded_file:
            errors.append("Could not download file.")
            self.poll_for_status("failed", 0, errors)
            return False
        
        if self.read_ndjson == True:
            data_batch = self.read_ndjson(downloaded_file, self.batch_offset, self.batch_size)
            res = callback(data_batch, errors, *args)
        else:
            res = callback(downloaded_file, errors, *args)

        if not res:
            errors.append("Error running function.")
            self.poll_for_status("failed", 0, errors)
            return False
        self.poll_for_status("succeeded", 1, errors)