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
	${COMPOSE} logs --timestamps mock_gateway --follow

dest-logs:
	${COMPOSE} logs --timestamps destination_app --follow

# ----- Testing -----

docker-test:
	${COMPOSE} run --rm test_app

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
	${COMPOSE} restart destination_app

# ----- Build Commands -----

docker-build:
	docker build -t "python_env:${IMAGE_VERSION}" -f "util/docker/Dockerfile" .

lambda-build:
	sh util/build.sh ${filename}
