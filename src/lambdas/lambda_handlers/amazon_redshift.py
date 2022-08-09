import boto3
import botocore.waiter
from datetime import datetime
from enum import Enum
import json
import logging
import os

from lambdas.amperity_runner import AmperityBotoRunner

logger = logging.getLogger(__name__)


REDSHIFT_CLIENT = boto3.client("redshift-data", region_name="us-east-1")
REDSHIFT_CLUSTER_ID = os.getenv("REDSHIFT_CLUSTER_ID")
REDSHIFT_DB_NAME = os.getenv("REDSHIFT_DB_NAME")
REDSHIFT_DB_USER = os.getenv("REDSHIFT_DB_USER")
REDSHIFT_IAM_ROLE = os.getenv("REDSHIFT_IAM_ROLE")
REDSHIFT_TABLE_NAME = os.getenv("REDSHIFT_TABLE_NAME")
S3_BUCKET = os.getenv("S3_BUCKET")


class WaitState(Enum):
    SUCCESS = 'success'
    FAILURE = 'failure'


class CustomWaiter:
    """
    https://docs.aws.amazon.com/code-samples/latest/catalog/python-demo_tools-custom_waiter.py.html
    Base class for a custom waiter that leverages botocore's waiter code. Waiters
    poll an operation, with a specified delay between each polling attempt, until
    either an accepted result is returned or the number of maximum attempts is reached.

    To use, implement a subclass that passes the specific operation, arguments,
    and acceptors to the superclass.

    For example, to implement a custom waiter for the transcription client that
    waits for both success and failure outcomes of the get_transcription_job function,
    create a class like the following:

        class TranscribeCompleteWaiter(CustomWaiter):
        def __init__(self, client):
            super().__init__(
                'TranscribeComplete', 'GetTranscriptionJob',
                'TranscriptionJob.TranscriptionJobStatus',
                {'COMPLETED': WaitState.SUCCESS, 'FAILED': WaitState.FAILURE},
                client)

        def wait(self, job_name):
            self._wait(TranscriptionJobName=job_name)

    """
    def __init__(
            self, name, operation, argument, acceptors, client, delay=5, max_tries=60,
            matcher='path'):
        """
        Subclasses should pass specific operations, arguments, and acceptors to
        their superclass.

        :param name: The name of the waiter. This can be any descriptive string.
        :param operation: The operation to wait for. This must match the casing of
                          the underlying operation model, which is typically in
                          CamelCase.
        :param argument: The dict keys used to access the result of the operation, in
                         dot notation. For example, 'Job.Status' will access
                         result['Job']['Status'].
        :param acceptors: The list of acceptors that indicate the wait is over. These
                          can indicate either success or failure. The acceptor values
                          are compared to the result of the operation after the
                          argument keys are applied.
        :param client: The Boto3 client.
        :param delay: The number of seconds to wait between each call to the operation.
        :param max_tries: The maximum number of tries before exiting.
        :param matcher: The kind of matcher to use.
        """
        self.name = name
        self.operation = operation
        self.argument = argument
        self.client = client
        self.waiter_model = botocore.waiter.WaiterModel({
            'version': 2,
            'waiters': {
                name: {
                    "delay": delay,
                    "operation": operation,
                    "maxAttempts": max_tries,
                    "acceptors": [{
                        "state": state.value,
                        "matcher": matcher,
                        "argument": argument,
                        "expected": expected
                    } for expected, state in acceptors.items()]
                }}})
        self.waiter = botocore.waiter.create_waiter_with_client(
            self.name, self.waiter_model, self.client)

    def __call__(self, parsed, **kwargs):
        """
        Handles the after-call event by logging information about the operation and its
        result.

        :param parsed: The parsed response from polling the operation.
        :param kwargs: Not used, but expected by the caller.
        """
        status = parsed

        for key in self.argument.split('.'):
            if key.endswith('[]'):
                status = status.get(key[:-2])[0]
            else:
                status = status.get(key)

        logger.info(
            "Waiter %s called %s, got %s.", self.name, self.operation, status)

    def _wait(self, **kwargs):
        """
        Registers for the after-call event and starts the botocore wait loop.

        :param kwargs: Keyword arguments that are passed to the operation being polled.
        """
        event_name = f'after-call.{self.client.meta.service_model.service_name}'
        self.client.meta.events.register(event_name, self)
        self.waiter.wait(**kwargs)
        self.client.meta.events.unregister(event_name, self)


class ExecuteStatementWaiter(CustomWaiter):
    def __init__(self, client):
        super().__init__(
            name='ExecuteStatementComplete',
            operation='DescribeStatement',
            argument='Status',
            acceptors={
                'COMPLETED': WaitState.SUCCESS,
                'FINISHED': WaitState.SUCCESS,
                'FAILED': WaitState.FAILURE,
                'ABORTED': WaitState.FAILURE
            },
            client=client)

    def wait(self, query_id):
        self._wait(Id=query_id)


class S3_Uploader:
    def __init__(self, bucket, file_type="data"):
        self.s3_client = boto3.client('s3')
        self.bucket = bucket
        self.file_type = file_type

    def bucket_exists(self):
        try:
            res = self.s3_client.head_bucket(Bucket=self.bucket)
            status_code = res["ResponseMetadata"]["HTTPStatusCode"]

            return status_code == 200

        except Exception as e:
            print(f"Could not find bucket {self.bucket}.", e)

            return False

    def create_ndjson(self, data):
        body = ""
        for i in data:
            body += json.dumps(i) + "\n"
        return body.encode("utf-8")

    def upload_data(self, data):
        if not self.bucket_exists():
            return False

        current_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        key = f"{self.file_type}/{current_timestamp}.ndjson"

        body = self.create_ndjson(data)

        try:
            print("Uploading file to S3.")
            self.s3_client.put_object(Body=body, Bucket=self.bucket, Key=key)
            s3_url = f"s3://{self.bucket}/{key}"
            print("Successfully uploaded file to S3.", s3_url)

            return s3_url

        except Exception as e:
            print("Error uploading file.", e)

            return False


class AmperityRedshiftRunner(AmperityBotoRunner):
    def table_exists(self, table_name):
        result = self.boto_client.list_tables(
            ClusterIdentifier=REDSHIFT_CLUSTER_ID,
            Database=REDSHIFT_DB_NAME,
            DbUser=REDSHIFT_DB_USER,
            TablePattern=REDSHIFT_TABLE_NAME
            )
        tables = result["Tables"]

        return len(tables) > 0

    def get_row_count(self, table_name):
        query = f"SELECT COUNT (*) FROM {table_name}"
        custom_waiter = ExecuteStatementWaiter(self.boto_client)
        res = self.boto_client.execute_statement(
            ClusterIdentifier=REDSHIFT_CLUSTER_ID,
            Database=REDSHIFT_DB_NAME,
            DbUser=REDSHIFT_DB_USER,
            Sql=query
            )
        id = res["Id"]

        try:
            print("Waiting for query...", query)
            custom_waiter.wait(query_id=id)

        except Exception as e:
            print("Error running query...", e)

            return None

        else:
            result = self.boto_client.get_statement_result(Id=id)
            row_count = result["Records"][0][0]["longValue"]
            print(f"Found {row_count} rows!")

            return row_count

    def copy_to_table(self, table_name, s3_url, iam_role):
        if not self.table_exists(table_name):
            message = "Table does not exist. Please create table in Redshift."
            self.errors.append(message)

        print(f"Redshift table {table_name} found.")

        curr_row_count = self.get_row_count(table_name)

        query = f"""
                copy {table_name}
                from '{s3_url}'
                iam_role '{iam_role}'
                json 'auto';"""

        custom_waiter = ExecuteStatementWaiter(self.boto_client)
        response = self.boto_client.execute_statement(
            ClusterIdentifier=REDSHIFT_CLUSTER_ID,
            Database=REDSHIFT_DB_NAME,
            DbUser=REDSHIFT_DB_USER,
            Sql=query
            )
        id = response["Id"]

        try:
            print("Waiting for query...", query)
            custom_waiter.wait(query_id=id)

        except Exception as e:
            message = "Error waiting for query." + str(e)
            self.errors.append(message)

        else:
            new_row_count = self.get_row_count(table_name)
            additional_rows = new_row_count - curr_row_count
            if not additional_rows:
                self.errors.append("No rows created.")

            success_message = f"INSERTED {additional_rows} ROWS"
            print(success_message)

    def runner_logic(self, data):

        s3_upload = S3_Uploader(bucket=S3_BUCKET)
        s3_url = s3_upload.upload_data(data)

        if not s3_url:
            return

        self.copy_to_table(REDSHIFT_TABLE_NAME, s3_url, REDSHIFT_IAM_ROLE)


def lambda_handler(event, context):
    payload = json.loads(event['body'])
    amperity_tenant_id = payload.get("tenant_id")

    pinpoint_runner = AmperityRedshiftRunner(
        payload,
        context,
        amperity_tenant_id,
        boto_client=REDSHIFT_CLIENT
    )

    status = pinpoint_runner.run()

    return status
