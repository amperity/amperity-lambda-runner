# Lambda Testing Environment

This project is based off of a hunch that we can have a lambda like environment locally for easier testing of ~60%? of our lambda logic.

The idea is two flask apps running in Docker. App 1 will be our lambda and it will implement the actual logic you want lambda to perform. App 2 will be a simple API to receive data from your "lambda" and log it for debugging. If this is possible/useful we can add simple logic to App 2 to test rate limiting, validation, timeouts, etc in our lambda.

## How to read

There's a good amount of stuff surrounding the lambda logic in this repo. Here's how to read what we have:

- `build/` The directory were your .zip'd lambda will go once you build it.
- `destinations/` A dummy flask app that is there to help with local development. All it does is log what it is sent and whatever validation you want to test.
- `lambdas/` The "core" part of this app. 
    - `lambdas/lambda_app.py` Is a flask app that acts as a mock lambda gateway trigger. It mimics the lambda context for your testing needs.
    - `lambdas/amperity_runner.py` The lambda logic written by Amperity devs to handle, hopefully, most of the logic for your lambda.
    - `lambdas/lambda_handlers/` A repository of custom handlers that you can reference for help.
- `test/` Repository for the test suite. Primarily used to test `amperity_runner` but if there's something you'd like to write for your handler feel free to add it!
- `util/` Where all the local development scripts, tools, etc live
- `docker-compose.yml` Where we define our local containers. 
    - `lambda_app` Our mock gateway container and entrypoint for the local environment
    - `destination_app` The debugging app
    - `fake_s3` A mock local S3 environment that holds file(s) for testing. 
- `Makefile` Easier to use commands for local development

The flow of development in this app is to copy an existing file in `lambdas/lambda_handlers/`, do some renaming, test configuration, build, and go!


## Developer notes


1. Test logic with larger datasets
1. Verify lambda timeout logic
    - Know when to end the lambda/kick off next
    - Know where to pick up from previous run
1. Wrtie the build script to make a .zip
1. Investigate localstack for lambda gateway/context for better local development

Do we want to write up an example of how to use/setup this environment?
There do not seem to be great resources for this stuff.


## Localstack Tests

How to use `fake_s3` for your local development. Using your CLI you can run `awscli` commands as you would and just override the endpoint to use. See below:

~~~
aws --endpoint-url=http://localhost:4566 s3 mb s3://test-bucket
aws --endpoint-url=http://localhost:4566 s3 ls s3://test-bucket
aws --endpoint-url=http://localhost:4566 s3 cp ./test/fixtures/example.ndjson s3://test-bucket
~~~

If you're inside a container you can reference `fake_s3` using it's name as the host. NOTE boto3 connecting to `fake_s3` from inside a container fails due to some endpoint validation inside AWS tools (both awscli & boto don't allow `fake_s3:4566` as a host) so you need to write files from outside the container and then use `requests` to read the file from inside the container. See below:

~~~python
import requests
resp = requests.get('http://fake_s3:4566/test-bucket/example.ndjson')
print(resp.content)
~~~


## Configuring your Env

1. Make sure you have `docker` running
1. `docker build -t "python_env:latest" -f "util/docker/Dockerfile" .`
    - This builds the image from the Dockerfile in `util/docker`
1. `docker-compose up -d`
    - Using the compose file at this level we launch our two apps.
1. (OPTIONAL) `docker run -it --rm {CONTAINER NAME HERE}`
    - This runs a container using that image, drops you into an interactive shell, and cleans up once you exit


## Workflow 

Either we have a long list in our docker-compose with env variables
OR
write a run script that does that. ie keep docker-compose cleaner

1. Local development using destination_app or your own destination
1. Write some tests with any new behavior
1. Build your lambda .zip (TODO how to do this)

Repo Structure:
~~~
README.md
docker-compose.yml
Makefile
destinations/
lambdas/
test/
util/
~~~

Build Script Output (as a .zip):
~~~
pip package(s)/
amperity_runner.py
app.py
~~~

## Notes


~~~
Lowest barier to entry

2 ways of developing. 
1) Write your own/copy and hold your own.
2) Add to our repo with tests as an example/reference

~~~

Webhook connector will send a request to the gateway with a pre-signed S3 url.
Using requests we can download the data into our script
Validate the json and create batches to send out to the destination API 

---

How to deploy:
Make sure any third party packages are installed in your directory with:
`pip install -t requests ./`

From the lambda dir zip the contents:
`zip -r test.zip ./`

On Lambda dashboard upload the zip file and deploy.

Double check that 'Runtime Settings' has the correct path to app.py.

---
Timeout Workflow:

1) We need to configure the lambda to our desired AWS enforced timeout.
2) We can track the remaining milliseconds with: context.get_remaining_time_in_millis()
3) We have an initial offset and a current offset while posting data.
4) When we are below 5? (depends on avg batch process time & request time) seconds left in the timeout we 
    kickoff another lambda using the offset of the running lambda.
5) Repeat until finished
6) Probably forgot something

TODO: Do we want a mock context class to have testing against?
    - Does this exist?


Potential Test Environment:
1) override webhook url in connector to localhost
2) webhook generate presigned url to aws-dev
3) the "wrapper" around the lambda kicks it off and tracks it
4) lambda runs and outputs to our dummy api that is just a flask app that logs the request

Two Docker containers running basic flask apps
Container 1:
    Has the 'lambda' in it, lambda control logic, and something else?

Container 2:
    Single endpoint receive data from 'lambda' and log/store it in memory for debugging.

---

Environment Setup:
~~~
export RS_APP_NAME=
export RS_WRITE_KEY=
~~~

https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-api-as-simple-proxy-for-lambda.html


Example `curl`:
~~~bash
curl -X POST -H 'x-api-key: {LAMBDA API KEY}' \
    -H '{"Content-Type": "Application/json"}' \
    -d  '{ "settings": {"audience_name": "Test Audience",}, "callback_url": "", "access_token": "top_secret", "data_url": "",}' \
    'https://4e8zmhav3e.execute-api.us-east-2.amazonaws.com/default/phil-test'
~~~


## Resources

https://bluesock.org/~willkg/blog/dev/using_localstack_for_s3.html
https://dev.to/goodidea/how-to-fake-aws-locally-with-localstack-27me
https://blog.jdriven.com/2021/03/running-aws-locally-with-localstack/
https://docs.localstack.cloud/aws/s3/
https://docs.localstack.cloud/aws/lambda/
