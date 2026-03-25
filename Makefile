.PHONY: up down build logs shell migrate test demo

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up -d --build

logs:
	docker compose logs -f web

shell:
	docker compose exec web python manage.py shell

migrate:
	docker compose exec web python manage.py migrate

test:
	docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test web python manage.py test tests/

demo:
	docker compose exec web python manage.py bootstrap_demo_data --reset
