build:
	docker-compose build

up:
	docker-compose up -d

test: up
	docker-compose run --rm --no-deps --entrypoint=uv api run pytest /tests/unit /tests/integration /tests/e2e

unit-tests:
	docker-compose run --rm --no-deps --entrypoint=uv api run pytest /tests/unit

integration-tests: up
	docker-compose run --rm --no-deps --entrypoint=uv api run pytest /tests/integration

e2e-tests: up
	docker-compose run --rm --no-deps --entrypoint=uv api run pytest /tests/e2e

logs:
	docker-compose logs --tail=25 api redis_pubsub

down:
	docker-compose down --remove-orphans

all: down build up test
