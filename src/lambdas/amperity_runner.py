import json

import requests

from helpers import http_response, rate_limit



class AmperityRunner:
    def __init__(self, payload, lambda_context, tenant_id, batch_size=2000, batch_offset=0):
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

        self.errors = []
        self.file_bytes = 0
        self.total_bytes = 0


    def poll_for_status(self, state, progress=0, reason=''):
        data = json.dumps({
            'state': state,
            'progress': progress,
            # NOTE - We aren't appending to this anywhere right now
            'errors': self.errors,
            'reason': reason
        })
        res = self.callback_session.put(self.status_url, data=data)

        print('Polling for status...', data, res)

        return res


    def runner_logic(self):
        pass


    def run(self):
        start_response = self.poll_for_status('running')

        # Do we want to kill a lambda if it can't report status to the app?
        if start_response.status_code != 200:
            return http_response(start_response.status_code, 'ERROR', 'Error polling for status.')

        head_resp = requests.head(self.data_url)
        self.file_bytes = int(head_resp.headers.get('Content-Length'))

        with requests.get(self.data_url, stream=True) as resp:
            if resp.status_code != 200:
                self.poll_for_status('failed', 0, reason='Failed to download file.')

                return resp

            self.process_stream(resp)

        # TODO - Math doesn't add up on this last call. Hardcode or figure out math problem?
        end_poll_response = self.poll_for_status('succeeded', 1)

        # TODO - We should return more than just the request object from poll_for_status
        return end_poll_response


    def process_stream(self, resp_stream):
        data_batch = []

        for i, row in enumerate(resp_stream.iter_lines()):
            # batch_offset should persist (be passed) b/w lambda runs if a timeout occurs.
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

                self.poll_for_status('running', round(self.total_bytes / self.file_bytes, 2))

        if len(data_batch) > 0:
            self.runner_logic(data_batch)


class AmperityAPIRunner(AmperityRunner):
    def __init__(self, *args, destination_url=None, destination_session=None, rate_limit=0, custom_mapping=None, data_key='data', **kwargs):
        super().__init__(*args, **kwargs)

        self.destination_url = destination_url
        self.destination_session = destination_session
        self.rate_limit = rate_limit
        self.custom_mapping = custom_mapping
        self.data_key = data_key

        self.num_requests = 0
        self.rate_limit_time_start = None

    @rate_limit
    def runner_logic(self, data):
        output_data = [self.custom_mapping(d) for d in data] if self.custom_mapping else data

        resp = self.destination_session.post(
            url=self.destination_url,
            data=json.dumps({self.data_key: output_data})
        )

        if resp.status_code != 200:
            print('POST failed: ')
            print(resp.content)
            self.errors.append(resp.content)

        print(output_data)
        self.num_requests += len(output_data)


class AmperityBotoRunner(AmperityRunner):
    def __init__(self, *args, boto_client=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not boto_client:
            raise NotImplementedError('Please supply a valid boto client')

        self.boto_client = boto_client


    def runner_logic(self, data):
        raise NotImplementedError('Please implement your boto runnder logic.')
