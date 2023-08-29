# Amperity Lambda Runner

Welcome to the Amperity Lambda runner repository, this project is designed to make it easy for you to write custom code against our [webhook destination](https://docs.amperity.com/datagrid/destination_webhook.html). The webhook destination allows you to write your own code, or what we provide, to work with data orchestrated out of your tenant. The webhook will generate the dataset with a pre-signed url in your tenant storage, trigger the lambda, and wait for status callbacks from the lambda. The rest of this README is about getting started quickly with local development, how to write your own lambda, and how to deploy it.


## Quickstart

To get started we recommend working locally in our docker environment to verify the functionality you want quickly. If you have a staging environment you can use then you will need to adjust the `destination_url` in the demo_lambda to use it. These three steps are designed to show that everything is working and you can iterate from there.

1. Run `make docker-build` and then `make up` to build and start the local environment.
1. Curl our [demo lambda](src/lambdas/lambda_handlers/demo_lambda.py) to execute the lambda as you would in AWS.
~~~sh
curl -X POST 'http://localhost:5555/lambda/demo_lambda' -H 'Content-Type: application/json' \
 -d '{"data_url": "http://fake_s3:4566/test-bucket/sample.ndjson", "callback_url": "http://api_destination:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'
~~~
3. Verify with `make logs` and look for "Lambda executed successfully" and "Recieved request with X records."

In [Developing with data from Amperity](#developing-with-data-from-amperity) we outline what's needed for writing any custom logic you need.


## Deploy your lambda

If you are using one of our existing Lambdas you can find instructions for downloading them using the AWS Serverless Repository on our [docs site](https://docs.amperity.com/datagrid/destination_webhook.html#serverless-destinations). Not all lambda handlers in this repository are finalized and deployed, if you see one that is wip please reach out to your Amperity contact and we'll give you an update on the work.

If you are writing a custom lambda handler and deploying it then follow the instructions in [Developing with data from Amperity](#developing-with-data-from-amperity). The easiest way is our make target that zips up the necessary files and you can manually upload it.


## Developing with data from Amperity

If you are looking to write your own Lambda this section gives you the items, and their order, you need to get that done. What "done" means for you lambda is up to you but the requirements from Amperity is that the status of the lambda is reported back to your tenant. This is why we recommend using `AmperityApiRunner` as that is baked into the behavior for you.

1. Create a copy of `src/lambdas/lambda_handlers/template.py` (in the same directory) with a descriptive name.
1. Choose the runner you should use for your implementation (probably `AmperityApiRunner`). Our `AmperityBotoRunner` is for writing data to another AWS service and requires knowledge of how that service is implemented in boto. `AmperityApiRunner` is a generic implementation for POSTing data to a destination API that requires configuring a requests session.
1. Create your `requests.Session` instance with the auth you need. This session object is used for batching records to your destination api. Optionally specify any batch sizes, rate limits, custom mapping, or custom keys you will need for your endpoint.
1. Do any testing you want in the local environment (see [example curls](#snippets)).
    - From an Amperity perspective "done" means you see "succeeded" in the mock report status and your destination has received all the records it needs.
1. Run `make lambda-build filename={ your filename.py here }` to build the zip file of your lambda.
1. Upload `build/lambda_handerl.zip` to your lambda app.
   - Set the "Handler" option in "Runtime Settings" to `app.lambda_handler`
   - Pick a desired timeout for your lambda in "Configuration -> General Configuration". The max is 15 minutes, and we recommend using that.
1. Test the deployed lambda by [manually invoking](#snippets) it or run the orchestration job in your Amperity tenant.

An AWS lambda has a max timeout of 15 minutes and depending on your dataset you might exceed that limit. If you run into this scenario Amperity is happy to work with you to find the best solution for your case but we do not offer a solution out of the box.


## Walk-through

There are plenty of tools in this repository to help you write your lambda logic. It is designed to be adaptable to your needs but if you see anything missing let us know.

When working locally there are several apps that are stood up. First is an API gateway app that we use to mimic a lambda environment. Second is a fake s3 container that operates the same as real S3 and holds a couple sample files. Third is an api destination you can use to inspect logs or test validation. By running `make logs` you can see the losgs of all these containers at once and use that to debug/verify your local lambda.


### Configuring your Env

We utilize `Make` to handle all the local development commands. Feel free to read that file to see everything at your disposal but below are most of the commands you'll need.

1. `make docker-build` builds the custom python image we use in this repo.
1. Optional: Update `docker-compose.yml` with any env variables you need.
1. `make up` brings up the 3 containers in `docker-compose.yml`.
    - You only need two of them (mock_gateway and fakes3) for regular development.

You now have a running environment! Below are a couple more helpful commands if you need to reset/debug odd behavior.

1. `make down` brings down all docker containers in this project.
1. `make sh` launches a new container using the python_env image for you to test in.
    - There are direct `sh` targets for already running containers (ie `make lambda-sh`). 
1. `make logs` Will display the logs from all containers from the time you run the command.
    - There are `logs` targets for individual containers if you want less clutter (ie `make lambda-logs`).


## Snippets

How to curl mock lambda:
~~~bash
curl -X POST 'http://localhost:5555/lambda/demo_lambda' \
    -H 'Content-Type: application/json' -d '{"data_url": "http://fake_s3:4566/test-bucket/sample.ndjson", "callback_url": "http://api_destination:5005/mock/poll/", "webhook_id": "wh-abcd12345"}'
~~~

How to curl a deployed lambda:
~~~bash
curl -X POST -H 'x-api-key: {{ lambda gateway api key }}' '{{ lambda api gateway url }}' \
    -H '{"Content-Type": "application/json"}' \
    -d '{"data_url": "http://some-bucket/example/sample.ndjson", "callback_url": "http://some-api.exampel/mock/poll/", "webhook_id": "wh-abcd12345"}'
~~~
