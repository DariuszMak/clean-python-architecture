build:
	docker-compose build

up:
	docker-compose up -d app

tests:
	pytest . --cov=.

logs:
	docker-compose logs app | tail -100

down:
	docker-compose down

all: down build up tests
