import json
import logging
import os

import requests

from urllib3 import Retry
from requests.adapters import HTTPAdapter
from requests.exceptions import RetryError

from lambdas.helpers import http_response, rate_limit


logger = logging.getLogger()
logger.setLevel(logging.getLevelName(os.getenv('LOG_LEVEL', default='INFO')))


class AmperityRunner:
    def __init__(self, payload, lambda_context, tenant_id, batch_size=500, batch_offset=0):
        """
        payload : dict
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
        tenant_id : str
            The slug of the tenant that invoked the lambda
        batch_size : int, optional
            Int representing how many records should go in a single outbound request
        batch_offset : int, optional
            If a single job cannot process all records this represents where the next job should pick up
        """
        self.lambda_context = lambda_context
        self.batch_size = batch_size
        self.batch_offset = batch_offset

        self.tenant_id = tenant_id
        self.data_url = payload.get('data_url')
        self.settings = payload.get('settings')
        self.access_token = payload.get('access_token')

        self.report_status_url = payload.get('callback_url') + payload.get('webhook_id')
        self.report_status_session = requests.Session()
        # NOTE - testing locally you will need to add a mount for 'http://'
        self.report_status_session.mount('https://', HTTPAdapter(max_retries=Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[502, 503, 504],
            allowed_methods={'PUT'},
        )))
        self.report_status_session.headers.update({
            'Content-Type': 'application/json',
            'X-Amperity-Tenant': self.tenant_id,
            'Authorization': f'Bearer {self.access_token}'
        })

        self.errors = []
        self.file_bytes = 0
        self.total_bytes = 0

    def report_status(self, state, progress=0.0, reason=''):
        """
        The orchestration in your Amperity tenant waits for status updates from the Lambda for 3 hours.
        This method executes these status updates ensuring the workflow in your tenant is accurate.

        We expect some errors to occur and do not want to overwhelm the status display in your tenant and slice to
        only 10 errors per batch. If the lambda fails the 'reason' field will display that information. We retry
        all calls to your tenant webhook 3 times with rules defined above in the HTTPAdapter.
        """
        res = None
        data = json.dumps({
            'state': state,
            'progress': progress,
            'errors': self.errors[:10],
            'reason': reason
        })

        logging.info(f'Reporting status to Amperity: {data}')

        try:
            res = self.report_status_session.put(self.report_status_url, data=data)
        except RetryError:
            logging.error('Exceeded retries trying to communicate with Amperity.')

        self.errors = []

        return res

    def runner_logic(self, data):
        pass

    def run(self):
        """
        Core logic method that manages the state of the lambda. First we tell Amperity that the Lambda
        has started and then begin streaming the file in. If either of these API calls fail we want
        the Lambda to fail fast and inform us.
        """
        start_response = self.report_status('running')

        if not start_response:
            return http_response(500, 'error', 'Error reporting status to Amperity. Ending Lambda.')

        with requests.get(self.data_url, stream=True) as stream_resp:
            if stream_resp.status_code != 200:
                logging.error('Failed to download file.')
                self.report_status('failed', 0, reason='Failed to download file.')

                return http_response(500, 'failed', 'Failed to download file.')

            self.file_bytes = int(stream_resp.headers.get('Content-Length'))
            self.process_stream(stream_resp)

        end_poll_response = self.report_status('succeeded', 1)

        return http_response(end_poll_response.status_code, 'succeeded', self.errors)

    def process_stream(self, stream_resp):
        """
        Method that handles all batching logic. There is logic to account for catching up if a previous
        lamba has failed partly through executing. See our docs on how best to pass this into a lambda execution.
        """
        data_batch = []

        for i, row in enumerate(stream_resp.iter_lines()):
            # We cannot stream to an offset so skip iterations while we are catching up.
            if self.batch_offset and i < self.batch_offset:
                continue

            # The +1 is to account for newline characters which are removed b/c of .iter_lines()
            self.total_bytes += len(row) + 1
            data = json.loads(row)

            if len(data_batch) < self.batch_size:
                data_batch.append(data)
            else:
                self.runner_logic(data_batch)
                data_batch = [data]
                self.batch_offset += self.batch_size

                self.report_status('running', round(self.total_bytes / self.file_bytes, 2))

        if len(data_batch) > 0:
            self.runner_logic(data_batch)


class AmperityAPIRunner(AmperityRunner):
    def __init__(self, *args, destination_url=None, destination_session=None, req_per_min=0, custom_mapping=None,
                 data_key=None, **kwargs):
        """
        Extension of the base AmperityRunner class designed to easily send data to an API endpoint.

        destination_url : str
            The endpoint the runner will send data to.
        destination_session : requests.Session
            A configured requests Session instance. It should have auth and headers already defined
        req_per_min : int, optional
            Integer to limit requests to the endpoint if it has a limit on requests per minute.
        custom_mapping : func, optional
            A custom function that does some data manipulation. It should return a dict
        data_key : str, optional
            If your endpoint has a specific key that data needs to stored in.
        """
        super().__init__(*args, **kwargs)

        self.destination_url = destination_url
        self.destination_session = destination_session
        self.req_per_min = req_per_min
        self.custom_mapping = custom_mapping
        self.data_key = data_key
        # NOTE - testing locally you will need to add a mount for 'http://'
        self.destination_session.mount('https://', HTTPAdapter(max_retries=Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[502, 503, 504],
            allowed_methods={'PUT', 'POST'},
        )))

        self.num_requests = 0
        self.rate_limit_time_start = None

    @rate_limit
    def runner_logic(self, data):
        mapped_data = self.custom_mapping(data) if self.custom_mapping else data
        output_data = json.dumps({self.data_key: mapped_data}) if self.data_key else json.dumps(mapped_data)

        try:
            resp = self.destination_session.post(
                url=self.destination_url,
                data=output_data
            )

            if not resp.ok:
                self.errors.append(resp.text)
        except RetryError as e:
            logging.error(f'Exceeded retries trying to communicate with destination. {self.destination_url}')
            self.errors.append(str(e))

        self.num_requests += len(output_data)


class AmperityBotoRunner(AmperityRunner):
    def __init__(self, *args, boto_client=None, **kwargs):
        """
        Extension of the base AmperityRunner class designed for AWS services.

        boto_client : boto3.client
            A valid boto3 Session.Client instance.
        """
        super().__init__(*args, **kwargs)

        if not boto_client:
            raise NotImplementedError('Please supply a valid boto client')

        self.boto_client = boto_client

    def runner_logic(self, data):
        raise NotImplementedError('Please implement your boto runnder logic.')
