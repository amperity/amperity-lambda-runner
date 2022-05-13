IMAGE_VERSION = latest
COMPOSE = docker-compose -p lambda_test


# ----- Local Development -----

up:
	${COMPOSE} up -d lambda_app

down:
	${COMPOSE} down -v

# ----- View Logs -----

# ${COMPOSE} logs --tail=0 --follow
logs:
	${COMPOSE} logs --follow

lambda-logs:
	docker logs lambda_test_lambda_app-1 --follow

dest-logs:
	docker logs lambda_test_destination_app-1 --follow

# ----- Testing -----

docker-test:
	${COMPOSE} run --rm test_app

# ----- Start/Connect to Containers -----

sh:
	docker run -it --rm python_env

lambda-sh:
	docker exec -it lambda_test-lambda_app-1 /bin/bash

dest-sh:
	docker exec -it lambda_test-destination_app-1 /bin/bash

# ----- Debug Helpers -----

restart:
	${COMPOSE} restart

restart-lambda:
	${COMPOSE} restart lambda_app

restart-dest:
	${COMPOSE} restart lambda_app

# ----- Build Commands -----

docker-build:
	docker build -t "python_env:${IMAGE_VERSION}" -f "util/docker/Dockerfile" .

lambda-build:
	sh util/build.sh
