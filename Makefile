flake8:
	flake8 --ignore=F405 .

black:
	black .

isort:
	isort .

base:
	pip install -r ./requirements/base.txt

local:
	pip install -r ./requirements/local.txt

production:
	pip install -r ./requirements/production.txt

build:
	docker compose -f local.docker-compose.yaml build

up:
	docker compose -f local.docker-compose.yaml up 

stop:
	docker compose -f local.docker-compose.yaml stop

down:
	docker compose -f local.docker-compose.yaml down

down-v:
	docker compose  -f local.docker-compose.yaml down -v

logs:
	docker compose -f local.docker-compose.yaml logs

api-logs:
	docker compose -f local.docker-compose.yaml logs api

db-logs:
	docker compose -f local.docker-compose.yaml logs db

worker-logs:
	docker compose -f local.docker-compose.yaml logs worker

flower-logs:
	docker compose -f local.docker-compose.yaml logs flower



beat-logs:
	docker compose -f local.docker-compose.yaml logs beat


status:
	docker ps

shell:
	docker exec -it api bash

makemigrations:
	docker exec api python manage.py makemigrations

migrate:
	docker exec api python manage.py migrate
	
superuser:
	docker exec -it api python manage.py createsuperuser

remove-all:
	docker compose -f local.docker-compose.yaml down --rmi all

pytest:
	docker exec -it api pytest

pytest-cov:
	docker exec -it api pytest -p no:warnings  --cov=. --cov-report html
