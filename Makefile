IMAGE_VERSION = latest
COMPOSE = docker-compose -p local_lambda


# ----- Local Development -----

up:
	${COMPOSE} up -d mock_gateway

down:
	${COMPOSE} down -v

# ----- View Logs -----

logs:
	${COMPOSE} logs --timestamps --tail=0 --follow

lambda-logs:
	docker logs --timestamps lambda-mock-gateway --follow

dest-logs:
	docker logs --timestamps lambda-destination-app --follow

# ----- Testing -----

docker-test:
	${COMPOSE} run --rm test_app

docker-test-class:
	${COMPOSE} run --rm test_app pytest test/test_amperity_runner.py::${class_name}

docker-test-func:
	${COMPOSE} run --rm test_app pytest test/test_amperity_runner.py::${class_name}::${func_name}

docker-type:
	${COMPOSE} run --rm test_app pycodestyle --max-line-length=140 src/ test/

# ----- Start/Connect to Containers -----

sh:
	docker run -it --rm python_env

lambda-sh:
	docker exec -it lambda-mock-gateway /bin/bash

dest-sh:
	docker exec -it lambda-destination-app /bin/bash

# ----- Debug Helpers -----

restart:
	${COMPOSE} restart

restart-lambda:
	${COMPOSE} restart lambda_gateway

restart-dest:
	${COMPOSE} restart api_destination

# ----- Build Commands -----

docker-build:
	docker build -t "python_env:${IMAGE_VERSION}" -f "util/docker/Dockerfile" .

lambda-build:
	sh util/build.sh ${filename}

sam-build:
	sh util/sam/sam-build.sh ${filename}

sam-publish:
	sam publish --template build/packaged.yaml --region ${region}
