.PHONY: up down build logs shell migrate test demo ci-test check-docker lint format coverage

check-docker:
	@command -v docker >/dev/null 2>&1 || { \
		echo "Error: Docker is not installed."; \
		echo "Please install Docker Desktop or Docker Engine from https://docs.docker.com/get-docker/"; \
		exit 1; \
	}
	@docker ps >/dev/null 2>&1 || { \
		echo "Error: Docker daemon is not running."; \
		echo "Please start Docker and try again."; \
		exit 1; \
	}

up: check-docker
	docker compose up -d

down:
	docker compose down

build: check-docker
	docker compose up -d --build

logs:
	docker compose logs -f web

shell:
	docker compose exec web python manage.py shell

migrate:
	docker compose exec web python manage.py migrate

test:
	docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test web python manage.py test tests/

ci-test:
	cd server && python manage.py test tests/

coverage:
	docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test web sh -c "pip install coverage -q && coverage run --source='apps' manage.py test tests/ && coverage report && coverage html"

demo:
	docker compose exec web python manage.py bootstrap_demo_data --reset

format:
	docker compose exec -w /app web black .
	docker compose exec -w /app web isort .

lint:
	docker compose exec -w /app web black --check .
	docker compose exec -w /app web isort --check-only .
