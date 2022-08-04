import json
import unittest.mock

import pytest
import requests

from lambdas.amperity_runner import AmperityRunner, AmperityAPIRunner, AmperityBotoRunner
from mock_services.lambda_gateway import LambdaContext


mock_event = {
    'callback_url': 'https://fake-callback.example/',
    'webhook_id': 'fake123',
    'data_url': 'https://fake-data.example/',
}
mock_context = LambdaContext()
mock_ndjson = '{"col1":"val1","col2":"val2"}\n{"col1":"val3","col2":"val4"}'
mock_headers = {'Content-Length': str(len(mock_ndjson.encode('utf-8')))}
destination_url = 'https://fake-destination.example/'
destination_sess = requests.Session()

class TestAmperityRunner:
    def test_construct_callback_session(self):
        test_runner = AmperityRunner(
            mock_event,
            mock_context,
            'test-tenant'
        )

        assert test_runner.callback_session is not None

    def test_happy_path(self, requests_mock):
        mock_data = requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123')
        mock_destination = requests_mock.post(destination_url, text='{"status":200}')

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
            data_key='data'
        )

        expected_request = json.dumps({"data": [{
            "col1": "val1",
            "col2": "val2"
        }, {
            "col1": "val3",
            "col2": "val4"
        }]})
        expected_poll_status = '{"state": "succeeded", "progress": 1, "errors": [], "reason": ""}'

        test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request

    def test_reports_download_failure_to_callback(self, requests_mock):
        requests_mock.get('https://fake-data.example/', text='Permissions Denied', status_code=403)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123')
        mock_destination = requests_mock.post(destination_url, text='{"status":200}')

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
        )
        expected_poll_status = '{"state": "failed", "progress": 0, "errors": [], "reason": "Failed to download file."}'

        test_runner.run()

        assert mock_destination.call_count == 0
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status

    def test_catch_up_to_offset(self, requests_mock):
        mock_data = requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123')
        mock_destination = requests_mock.post(destination_url, text='{"status":200}')

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
            batch_size=1,
            batch_offset=1,
            data_key='data'
        )

        expected_request = json.dumps({"data": [{
            "col1": "val3",
            "col2": "val4"
        }]})
        expected_poll_status = '{"state": "succeeded", "progress": 1, "errors": [], "reason": ""}'

        test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request

    def test_lambda_timeout(self):
        pass


class TestAmperityAPIRunner:
    @unittest.mock.patch('lambdas.helpers.sleep')
    def test_rate_limit(self, sleep_mock, requests_mock):
        mock_data = requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123')
        mock_destination = requests_mock.post(destination_url, text='{"status":200}')

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
            batch_size=1,
            req_per_min=1,
        )
        test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 2
        assert mock_callback.call_count == 3
        assert sleep_mock.call_count == 1

    @unittest.mock.patch.object(LambdaContext, 'get_remaining_time_in_millis', return_value=300)
    @unittest.mock.patch('boto3.client')
    def test_lambda_timeout(self, boto_mock, context_mock, requests_mock):
        mock_data = requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123')
        mock_destination = requests_mock.post(destination_url, text='{"status":200}')

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
            batch_size=1,
            req_per_min=1,
        )
        test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 0
        assert mock_callback.call_count == 3
        assert context_mock.call_count == 2
        assert boto_mock.call_count == 2

    def test_custom_mapping(self, requests_mock):
        mock_data = requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123')
        mock_destination = requests_mock.post(destination_url, text='{"status":200}')

        def add_customer_id(data):
            return [dict(d, **{
                'userId': d['cust_id'] if 'cust_id' in d else 1234,
                'type': 'track',
                'event': 'Product Purchased'
                }) for d in data]

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
            custom_mapping=add_customer_id,
            data_key='data'
        )

        expected_request = json.dumps({"data": [{
            "col1": "val1",
            "col2": "val2",
            "userId": 1234,
            "type": "track",
            "event": "Product Purchased"
        }, {
            "col1": "val3",
            "col2": "val4",
            "userId": 1234,
            "type": "track",
            "event": "Product Purchased"
        }]})
        expected_poll_status = '{"state": "succeeded", "progress": 1, "errors": [], "reason": ""}'

        test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request

    def test_dynamic_keyword(self, requests_mock):
        mock_data = requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123')
        mock_destination = requests_mock.post(destination_url, text='{"status":200}')

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
            data_key="batch"
        )

        expected_request = json.dumps({"batch": [{
            "col1": "val1",
            "col2": "val2"
        }, {
            "col1": "val3",
            "col2": "val4"
        }]})
        expected_poll_status = '{"state": "succeeded", "progress": 1, "errors": [], "reason": ""}'

        test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request

    def test_tracks_request_errors(self, requests_mock):
        mock_data = requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123')
        mock_destination = requests_mock.post(destination_url, text='{"status":400, "message":"error message"}', status_code=400)

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
            data_key='data'
        )

        expected_request = json.dumps({"data": [{
            "col1": "val1",
            "col2": "val2"
        }, {
            "col1": "val3",
            "col2": "val4"
        }]})
        expected_poll_status = '{"state": "succeeded", "progress": 1, ' \
                               '"errors": ["{\\"status\\":400, \\"message\\":\\"error message\\"}"], "reason": ""}'

        test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request


class TestAmperityBotoRunner:
    def test_boto_runner_raises_init_exception(self):
        with pytest.raises(NotImplementedError) as e:
            AmperityBotoRunner(
                mock_event,
                mock_context,
                'test-tenant',
            )

        assert e.type is NotImplementedError

    def test_boto_runner_raises_runner_logic_exception(self, requests_mock):
        requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        requests_mock.put('https://fake-callback.example/fake123')

        boto_runner = AmperityBotoRunner(
            mock_event,
            mock_context,
            'test-tenant',
            boto_client='fake-boto-client'
        )

        with pytest.raises(NotImplementedError) as e:
            boto_runner.run()

        assert e.type is NotImplementedError