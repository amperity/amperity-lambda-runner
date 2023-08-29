# Amperity Lambda Runner Testing

There is a test suite we maintain to assert our AmperityRunner logic. If you would like to write pytests against a specific lambda handler you are more than welcome but it is not required. 

Locally we do provide a "full" environment for you to use. Below is a rough outline of what services we provide, how you can use them, and some notes on maintaining them.

## Local Tests

We use [pytest](https://docs.pytest.org/en/latest/getting-started.html) for our automated testing. The structure is straightforward, and you can add to it by creating a new file in `test/`. 

To run the full test suite use the make command: `make docker-test`
If you'd like to run a specific test class use this make command: `make docker-test-class class_name=TestAmperityRunner`
If you'd like to run a specific test function use this make command: `make docker-test-func class_name=TestAmperityRunner func_name=test_catch_up_to_offset`

The existing automated tests are there to assert core `AmperityRunner` logic not any of the handlers. We may revisit this in the future but for now it's not an area of focus.

## Containers

## Localstack Notes

> *NOTE* Version 2.0 of Localstack introduced breaking changes. If we need to upgrade the image version > 2 it's worth investigating other local fake s3 alternatives (ie minio).

Localstack seems very powerful and helpful, however, it has rather poor documentation from what I could dig up. This section is a semiformal walk-through of how we use it in case you need to do something similar.

The main use case I wanted to support was having files populated in the S3 container after it was initialized. There are workaround ways we could have used but localstack supports custom initialization scripts on container start. We utilize that to run some aws cli commands against the container.

Any files in `/docker-entrypoint-initaws.d/` will be executed on startup. With a custom init script we can look for any .ndjson files in `test/fixtures` and upload them to the new S3 container.
I didn't dig into the localstack init scripts but had issues mounting fixture files to load into the environment. Best workflow I found was to mount the volumes in `/tmp/localstack/` so we didn't override any of the important files.

Helpful snippets below.

How to use `fake_s3` for your local development. Using your CLI you can run `awscli` commands as you would and just override the endpoint to use. See below:

~~~
aws --endpoint-url=http://localhost:4566 s3 mb s3://test-bucket
aws --endpoint-url=http://localhost:4566 s3 ls s3://test-bucket
aws --endpoint-url=http://localhost:4566 s3 cp ./test/fixtures/sample.ndjson s3://test-bucket
~~~

If you're inside a container you can reference `fake_s3` using it's name as the host. 

~~~python
import requests
resp = requests.get('http://fake_s3:4566/test-bucket/sample.ndjson')
print(resp.content)
~~~

NOTE boto3 connecting to `fake_s3` from inside a container fails due to endpoint validation inside AWS tools (both awscli & boto don't allow `fake_s3:4566` as a host) so you need to write files from outside the container and then use `requests` to read the file from inside the container.

## Snippets

How to curl mock lambda:
~~~bash
curl -X POST 'http://localhost:5555/lambda/{{ lambda filename (no .py )}}' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/sample.ndjson", "callback_url": "http://api_destination:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'
~~~

How to curl a deployed lambda:
~~~bash
curl -X POST -H 'x-api-key: {{ lambda gateway api key }}' '{{ lambda api gateway url }}' \
    -H '{"Content-Type": "application/json"}' \
    -d '{"data_url": "http://some-bucket/example/sample.ndjson", "callback_url": "http://some-api.exampel/mock/poll/", "webhook_id": "wh-abcd12345"}'
~~~

The shape of the body that your lambda will be invoked with:
~~~json
{
    "settings": {"some": "setting"},
    "label_name": "test label",
    // The s3 url where the data is living
    "data_url": "http://fake_s3:4566/test-bucket/sample.ndjson",
    // Token used to authorize the request with amperity API
    "access_token": "2:somevarchar:anothervarchar",
    // Identifier for the specific webhook job you are currently processing
    "webhook_id": "wh-somevarchar",
    // The endpoint to send the status request to
    "callback_url": "https://app.amperity.com/webhook/v1/"
}
~~~
