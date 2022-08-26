# Amperity Lambda Runner

Welcome to the Amperity Lambda runner repository, this project is designed to make it easy for you to write custom code against our Webhook Destination. There is a full toolset for local development if you need it, or you can write your code here and use the build script to install any necessary packages. 

## AWS Serverless Application Repository

We will try to upload and maintain all files you see in `lambda_handlers/` on the AWS Serverless Application Repository. These applications will almost always require minimal configuration while deploying from the store. The main exception is our generic API application as it is designed to be used for any API you need to integrate with. There are specific READMEs for each application in `docs/apps/` if you want to learn more about what they do. If you are looking to understand how we deploy using SAM CLI take a look at `docs/deployments.md`. 

The rest of this README is focused on how to use this repostiory yourself to write a lambda handler and deploy it. 

## Quickstart

The places you need to put things and commands you need to get a basic project up in lambda quickly with no local testing. Following sections will cover the repository in more depth.

1. Create a copy of `src/lambdas/lambda_handlers/template.py` (in the same directory) with a descriptive name
1. Choose the runner you should use for your implementation (probably `AmperityApiRunner`)
1. Create your `requests.Session` instance with whatever auth you need. Optionally specify any batch sizes, rate limits, custom mapping, or custom keys you will need for your endpoint.
1. Optional: Use the local environment for testing (see [Local Development](#local-development))
1. Run `make lambda-build filename={ your filename.py here }`
1. Upload `build/lambda_handerl.zip` to your lambda app.
   - Set the "Handler" option in "Runtime Settings" to `app.lambda_handler`
   - Pick a desired timeout for your lambda in "Configuration -> General Configuration". The max is 15 minutes, and we recommend using that.
1. Test the deployed lambda by [manually invoking](docs/testing.md#snippets) it or run the orchestration job in your Amperity tenant.

## Walk-through

There are plenty of tools in this repository to help you write your lambda logic. It is designed to be adaptable to your needs but if you see anything missing let us know.

When working locally there are several apps that are stood up. First is an API gateway app that we use to mimic a lambda environment. Second is a fake s3 container that operates the same as real S3 and holds a couple sample files. Third is an api destination you can use to inspect logs or test validation.

### Configuring your Env

We utilize `Make` to handle all the local development commands. Feel free to read that file to see everything at your disposal but below are most of the commands you'll need.

1. `make docker-build` builds the custom python image we use in this repo.
1. Optional: Add any environment variables your lambda will need to `.env`.
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

## Notes

See the `docs/` directory for more detailed explanations on deploying, testing, or specific handlers. 

### Developer notes

List of features we want to implement.

1. The lambda API gateway will timeout the connection after ~3 minutes and our app will receive a 500. 
    - Is there a good/easy to use template we can make where the lambda_handler parses the body, launches the actual "logic lambda", and returns 200 to the app?

## Resources

https://bluesock.org/~willkg/blog/dev/using_localstack_for_s3.html
https://dev.to/goodidea/how-to-fake-aws-locally-with-localstack-27me
https://blog.jdriven.com/2021/03/running-aws-locally-with-localstack/
https://docs.localstack.cloud/aws/s3/
https://docs.localstack.cloud/aws/lambda/

https://github.com/tomasbasham/ratelimit/blob/master/ratelimit/decorators.py
https://github.com/icecrime/RateLimiting/blob/master/ratelimiting.py
https://github.com/RazerM/ratelimiter/blob/master/ratelimiter/_sync.py
