# Amperity Lambda Runner

Welcome to the Amperity Lambda runner repository, this project is designed to make it easy for you to write custom code against our Webhook Destination. There is a full toolset for local development if you need it, or you can write your code here and use the build script to install any necessary packages. 

## Quickstart

The places you need to put things and commands you need to get a basic project up in lambda quickly with no local testing. Following sections will cover the repository in more depth.

1. Create a copy of `src/lambdas/lambda_handlers/template.py` (in the same directory) with a descriptive name
1. Choose the runner you should use for your implementation (probably `AmperityApiRunner`)
1. Create your `requests.Session` instance with whatever auth you need. Optionally specify any batch sizes, rate limits, data mapping, or custom keys you will need for your endpoint.
1. Optional: Use the local environment for testing (ie [Local Development](#local-development))
1. Run `make lambda-build filename={ your filename.py here }`
1. Upload `build/lambda_handerl.zip` to your lambda app.
   - Set the "Handler" option in "Runtime Settings" to `app.lambda_handler`
   - Pick a desired timeout for your lambda in "Configuration -> General Configuration". The max is 15 minutes, and we recommend using that.
1. Test the deployed lambda by [manually invoking](#snippets) it or run the orchestration job in your Amperity tenant.

## Walk-through

There are plenty of tools in this repository to help you write your lambda logic. It is designed to be adaptable to your needs but if you see anything missing let us know.

When working locally there are several apps that are stood up. First is an API gateway app that we use to mimic a lambda environment. Second is a fake s3 container that operates the same as real S3 and holds a couple sample files. Third is an api destination you can use to inspect logs or test validation.

### Configuring your Env

We utilize `Make` to handle all the local development commands. Feel free to read that file to see everything at your disposal but below are the commands needed to get up and running quick.

1. `make docker-build` builds the custom python image we use in this repo.
1. Add any environment variables your lambda will need to `.env`.
    - This file *is* tracked by git so make sure to remove any actual secrets before you commit.
1. `make up` brings up the 3 containers in the `docker-compose.yml` file.
    - You only need two of them (mock_gateway and fakes3) for regular development.

You now have a running environment! Below are a couple more helpful commands if you need to reset/debug odd behavior.

1. `make down` brings down all docker containers in this project.
1. `make sh` launches a new container using the python_env image for you to test in.
    - There are `sh` targets for already running containers.
1. `make logs` Will display the logs from all containers from the time you run the command.
    - There are `logs` targets for individual containers if you want less clutter.

The next section will include the rest and how to develop in this environment.

### Local development

This repository is designed around our Docker environment which makes invoking python scripts directly on your machine difficult. The recommended approach is to `make up` the Docker env,  [curl the mock gateway](#snippets), and inspect the logs for debugging.

We recommend using `curl` for local testing as it is closer to the real lambda environment but understand that it is easier to start with directly invoking the python script. If you want to do that you can start the Docker environment (`make up`), connect to the mock gateway container (`make lambda-sh`), and then do all your development commands from inside that container. Using this environment will provide all the packages you need and does live reload the code as you change things in your handler.

If you need to get custom data (ie a query from your Amperity tenant) into the fake S3 environment then below will walk you through how to do that. 

First, you need to identify the type of data you are processing in your lambda. Our recommended approach is to use the `Queries` tab in your amperity app to do as much processing in SQL as possible (ie rename fields, calculate values, etc) and then send that file through an orchestration to lambda. However, this first lambda should be a no-op and simply log the `data_url` field to cloudwatch and return a 200. Grab that `data_url` and paste it into your browser to download it the file to your computer. In this repository move it `test/fixtures/` so whenever you run `make up` that file will be in fakes3 and available for testing.

Hopefully, our `AmperityAPIRunner` cover the use case you need but if it does not feel free to open an issue/PR with the changes. If what you're doing is really not supported then feel free to write your own runner logic by extending the base `AmperityRunner` class.

### Repository structure

- `build/` The directory were your .zip'd lambda will go once you build it.
- `src/mock_services/` Where the development Flask apps live.
- `src/lambdas/` The "core" part of this app.
    - `lambdas/amperity_runner.py` The lambda logic written by Amperity devs to handle, hopefully, most of the logic for your lambda.
    - `lambdas/lambda_handlers/` Where you should write your lambda handler. Other custom handlers that you can reference for help.
- `test/` Repository for the test suite. Primarily used to test `amperity_runner` but if there's something you'd like to write for your handler feel free to add it!
    - `test/fixtures` Any file with a .ndjson extension put into this folder will be hosted in fakes3 when the docker containers are launched.
- `util/` Where all the local development scripts, tools, etc live
- `docker-compose.yml` Where we define our local containers.
- `Makefile` Easier to use commands for local development.

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

## How to setup IAM permissions

If you are handling large amounts of data your lambda could reach the timeout enforced by AWS. This section explains how to configure the IAM policies necessary for your lambda to invoke itself and continue working. This is considered an anti-pattern by AWS but given the tools we can use it is the simplest solution for long-running jobs.

1. Copy function arn from your lambda page. (Function overview on the right side under description)
1. Open `Configuration -> Permissions` and open role associated with this lambda. (ie `Execution Role`)
1. In the new tab go to `Add permissions` and select `Attach policies`
1. You'll be moved to a new page and there you'll select `Create Policy`
1. Navigate to the JSON tab and copy in the below json. Make sure to replace `Resource` with your function arn.
~~~json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowLambdaToInvokeLambda",
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "arn:aws:lambda:us-east-2:884752987182:function:phil-test"
        }
    ]
}
~~~
1. Create the policy and attach it to the lambda's role. 
1. You are good to go!

## Notes

This is primarily a section for maintainers to use and reference going forward.

### Testing

We use [pytest](https://docs.pytest.org/en/7.1.x/getting-started.html) for our automated testing. The structure is straightforward, and you can add to it by creating a new file in `test/`. 

To run the full test suite use the make command: `make docker-test`
If you'd like to run a specific test class use this make command: `make docker-test-class class_name=TestAmperityRunner`
If you'd like to run a specific test function use this make command: `make docker-test-func class_name=TestAmperityRunner func_name=test_catch_up_to_offset`

The existing automated tests are there to assert core `AmperityRunner` logic not any of the handlers. We may revisit this in the future but for now it's not an area of focus.


### Localstack Notes

Localstack seems very powerful and helpful, however, it has rather poor documentation from what I could dig up. This section is a semiformal walk-through of how we use it in case you need to do something similar.

The main use case I wanted to support was having files populated in the S3 container after it was initialized. There are workaround ways we could have used but after some stackoverflow 

https://aws.plainenglish.io/localstack-resource-creation-on-initialization-a86c2ce42310
https://docs.localstack.cloud/localstack/configuration/

Any files in `/docker-entrypoint-initaws.d/` will be executed on startup. Wrote a custom init script and threw it in there to load our files.
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


### Developer notes

List of features we want to implement.

1. The lambda API gateway will timeout the connection after ~3 minutes and our app will receive a 500. 
    - Is there a good/easy to use template we can make where the lambda_handler parses the body, launches the actual "logic lambda", and returns 200 to the app?
1. Investigate localstack for lambda gateway/context for better local development


## Resources

https://bluesock.org/~willkg/blog/dev/using_localstack_for_s3.html
https://dev.to/goodidea/how-to-fake-aws-locally-with-localstack-27me
https://blog.jdriven.com/2021/03/running-aws-locally-with-localstack/
https://docs.localstack.cloud/aws/s3/
https://docs.localstack.cloud/aws/lambda/

https://github.com/tomasbasham/ratelimit/blob/master/ratelimit/decorators.py
https://github.com/icecrime/RateLimiting/blob/master/ratelimiting.py
https://github.com/RazerM/ratelimiter/blob/master/ratelimiter/_sync.py
