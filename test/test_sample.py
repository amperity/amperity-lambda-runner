import pytest

from lambdas.test_lambda import lambda_handler
import lambdas.test_lambda as test_lambda


class TestLambdas:
    def setUp(self):
        print('Configuring test env')

    def test_no_env_variables(self, monkeypatch):
        # NOTE: Leaving these here as an example of how to patch
        #   env variables.
        monkeypatch.setenv('RS_APP_NAME', 'fake')
        monkeypatch.setenv('RS_WRITE_KEY', 'key')

        assert lambda_handler({}, {}) == None


    def test_bad_event_body(self, monkeypatch):
        monkeypatch.setattr(test_lambda, 'RS_APP_NAME', 'fake')
        monkeypatch.setattr(test_lambda, 'RS_WRITE_KEY', 'key')

        with pytest.raises(Exception) as e:
            print(e)
            lambda_handler({} ,{})
            assert True

    def test_catch_up_to_offset():
        pass

    def test_api_runner():
        pass

    def test_boto_runner():
        pass
