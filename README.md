# Lambda Testing Environment

This project serves two main purposes. First, it is a library of lambda_handlers written by amperity devs with some helpful runner logic to abstract away general use cases. Second, it is a "full" local lambda-like environment for your development needs. What that mostly means is there is a flask app that acts as the lambda API gateway that you can curl to trigger and a fakes3 that holds sample files you can write logic against. 

More notes and refinement coming soon!

## How to read

There's a good amount of stuff surrounding the lambda logic in this repo. Here's how to read what we have:

- `build/` The directory were your .zip'd lambda will go once you build it.
- `destinations/` A dummy flask app that is there to help with local development. All it does is log what it is sent and whatever validation you want to test.
- `lambdas/` The "core" part of this app. 
    - `lambdas/lambda_gateway.py` Is a flask app that acts as a mock lambda gateway trigger. It mimics the lambda context for your testing needs.
    - `lambdas/amperity_runner.py` The lambda logic written by Amperity devs to handle, hopefully, most of the logic for your lambda.
    - `lambdas/lambda_handlers/` A repository of custom handlers that you can reference for help.
- `test/` Repository for the test suite. Primarily used to test `amperity_runner` but if there's something you'd like to write for your handler feel free to add it!
    - `test/fixtures` Any file with a .ndjson extension put into this folder will be hosted in fakes3 when the docker containers are launched.
- `util/` Where all the local development scripts, tools, etc live
- `docker-compose.yml` Where we define our local containers. 
    - `lambda_gateway` Our mock gateway container and entrypoint for the local environment
    - `destination_app` The debugging app
    - `fake_s3` A mock local S3 environment that holds file(s) for testing.
- `Makefile` Easier to use commands for local development

The flow of development in this app is to copy an existing file in `lambdas/lambda_handlers/`, do some renaming, test configuration, build, and go!



## Configuring your Env

We utilize Make to handle all the local development commands. Feel free to read that file to see everything at your disposal but below are the commands needed to get up and running quick.

1. `make docker-build` builds the custom python image we use in this repo.
1. Add any environment variables your lambda will need to `.env`.
    - This file *is* tracked by git so make sure to remove any actual secrets before you commit.
1. `make up` brings up the 3 containers in the docker-compose.yml file.
    - You only need two of them (mock_gateway and fakes3) for regular development.

You now have a running environment! Below are a couple more helpful commands if you need to reset/debug odd behavior.

1. `make down` brings down all docker containers in this project.
1. `make sh` launches a new container using the python_env image for you to test in.
1. `make logs` Will display the logs from all containers from the time you run the command.

There are more commands in Makefile you can use and feel free to add some yourself! These are most of the common commands you will need to use this repo.

The next section will include the rest and how to develop in this environment.


## Workflow 

First, you need to identify the type of data you are processing in your lambda. Our recommended approach is to use the `Queries` tab in your amperity app to do as much processing in SQL as possible (ie rename fields, calculate values, etc) and then send that file through an orchestration to lambda. However, this first lambda should be a no-op and simply log the `data_url` field to cloudwatch and return a 200. Grab that `data_url` and paste it into your browser to download it to your computer and move it `test/fixtures/`. Now whenever you run `make up` that file will be in fakes3 and available for testing.

Next, you can work on your lambda logic however makes the most sense for you. The only mock services we provide in this project are S3 and an API. If you would like to write automated tests you can use the test directory for that. 

Once you have finished your lambda logic and want to test the end to end processs you can build your lambda. 

`make lambda-build filename={{ file in lambda_handlers/ }}`

This will output a file called `lambda_handler.zip` in the build directory. In the lambda dashboard use the "Upload From" dropdown, select ".zip file", and navigate to wherever that `lambda_handler.zip` is on your computer. 

The final configuration for you lambda is in AWS. Set the "Handler" option in "Runtime Settings" to `app.lambda_handler`. Finally pick a desired timeout for your lambda in "Configuration -> General Configuration". The max is 15 minutes so we recommend using that.


## How to setup IAM permissions
First step is to copy function arn from your lambda page. (Function overview on the right side under description)

Second step is open `Configuration -> Permissions` and open role associated with this lambda. (ie `Execution Role`)

In the new tab go to `Add permissions` and select `Attach policies`

You'll be moved to a new page and there you'll select `Create Policy`

Navigate to the JSON tab and copy in the below json. Make sure to replace `Resource` with your function arn.

~~~

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

Create the policy and attach it to the lambda's role. 

You are good to go!


## AWS Connect Notes

Writing this here as an initial set of notes for how to use this repo to test a new lambda you are working on.

1. Create Query, Destination, Orchestration, etc in noodles tenant.
1. Create new Lambda called aws_conenct & create gateway for it
1. Upload a version of the aws_connect.py lambda that logs the data_url only.
1. Grab the data_url from the cloudwatch logs and paste into browser to download the file locally
1. Move that file from downloads into test/fixtures ane run `make up`.
1. Write logic using fakes3 file and test logic.
1. Build and upload finished version of aws_connect.py (ie `make lambda-build filename=aws_connect.py`)
1. Test a full run of Orchestration -> Lambda -> AWS Connect App
    - You'll probably need to bump the timeout on the lambda. 100 records takes ~10 seconds to complete.


## Notes

The shape of the body in the request will have these fields
~~~json
{
    "settings": {"some": "setting"},
    "label_name": "test label",
    // The s3 url where the data is living
    "data_url": "http://fake_s3:4566/test-bucket/sample.ndjson",

    // Everything below is only necessary if you are testing status logic in the amperity system
    
    // Token used to authorize the request with amperity API
    "access_token": "2:SbHdltrCSX2zbMZrutK4lw:e43c14cc893309e28a0bbd94d06fb44138cc3383492b00de548a7fc437aa3280",
    // Identifier for the specific webhook job you are currently processing
    "webhook_id": "wh-9tftMuJD7qnjuH6MvPUcbR",
    // The endpoint to send the status request to
    "callback_url": "https://app.amperity.com/webhook/v1/"
}
~~~

How to curl mock lambda:
~~~bash
curl -X POST 'http://localhost:5555/lambda/{{ lambda filename (no .py )}}' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/sample.ndjson"}'
~~~

How to curl a deployed lambda:
~~~bash
curl -X POST -H 'x-api-key: {{ lambda gateway api key }}' '{{ lambda api gateway url }}' \
    -H '{"Content-Type": "application/json"}' \
    -d '{ "label_name": "test label", "settings": {}, "data_url": "http://some-s3-bucket.example/filename" }'
~~~


## Localstack Notes

Localstack seems very powerful and helpful, however, it has rather poor documentation from what I could dig up. This section is a semi-formal walkthrough of how we use it in case you need to do something similar.

Rough notes below. Want to do a more thorough dive through their documentation/the couple blog posts I saw and then flesh this out.

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


## Developer notes

Put things here so we have a somewhat comprehensive list of features we want to implement.

1. Test logic with larger datasets.
    - `aws_connect.py` implements a rough attempt at this. Stream in results from S3 so we don't run out of memory.
1. Verify lambda timeout logic
    - Write up IAM permission formal notes
    - The initiation of the lambda is a gateway event and body comes in as a string we cast to dict. Boto3 invocation brings in an actual dict and our parsing logic falls apart.
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
