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
    def test_construct_report_status_session(self):
        test_runner = AmperityRunner(
            mock_event,
            mock_context,
            'test-tenant'
        )

        assert test_runner.report_status_session is not None

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

        expected_result = {"statusCode": 200, "body": json.dumps({"status": "succeeded", "message": []})}
        result = test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request
        assert result == expected_result

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

        expected_result = {"statusCode": 500, "body": json.dumps({"status": "failed", "message": "Failed to download file."})}
        result = test_runner.run()

        assert mock_destination.call_count == 0
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert result == expected_result

    def test_report_status_retries(self, requests_mock):
        requests_mock.get('https://fake-data.example/', text=mock_ndjson, headers=mock_headers)
        mock_callback = requests_mock.put('https://fake-callback.example/fake123', status_code=502)
        mock_destination = requests_mock.post(destination_url, text='{"status":200}')

        test_runner = AmperityAPIRunner(
            mock_event,
            mock_context,
            'test-tenant',
            destination_url=destination_url,
            destination_session=destination_sess,
        )

        expected_result = {"statusCode": 500, "body": json.dumps({"status": "error", "message": "Error reporting status to Amperity. Ending Lambda."})}
        result = test_runner.run()

        print(mock_callback.request_history)

        assert mock_destination.call_count == 0
        assert mock_callback.call_count == 1
        assert result == expected_result 

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

        expected_result = {"statusCode": 200, "body": json.dumps({"status": "succeeded", "message": []})}
        result = test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request
        assert result == expected_result

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

        expected_result = {"statusCode": 200, "body": json.dumps({"status": "succeeded", "message": []})}
        result = test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 2
        assert mock_callback.call_count == 3
        assert sleep_mock.call_count == 1
        assert result == expected_result

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

        expected_result = {"statusCode": 200, "body": json.dumps({"status": "succeeded", "message": []})}
        result = test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request
        assert result == expected_result

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

        expected_result = {"statusCode": 200, "body": json.dumps({"status": "succeeded", "message": []})}
        result = test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request
        assert result == expected_result

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

        expected_result = {
            'statusCode': 200,
            'body': '{"status": "succeeded", "message": []}'}
        result = test_runner.run()

        assert mock_data.call_count == 1
        assert mock_destination.call_count == 1
        assert mock_callback.call_count == 2
        assert mock_callback.last_request.text == expected_poll_status
        assert mock_destination.last_request.text == expected_request
        assert result == expected_result


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
