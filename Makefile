.PHONY: help up down logs logs-backend logs-bot logs-worker logs-beat logs-postgres logs-redis migrate shell-backend shell-bot shell-postgres backup clean prod-up prod-down prod-logs test lint format

COMPOSE_FILE := docker-compose.yml
PROD_COMPOSE_FILE := docker-compose.prod.yml
COMPOSE := docker-compose -f $(COMPOSE_FILE)
PROD_COMPOSE := docker-compose -f $(PROD_COMPOSE_FILE)

help:
	@echo "VPN Sales System - Available Commands"
	@echo "====================================="
	@echo ""
	@echo "Development Commands:"
	@echo "  make up                 - Start development containers"
	@echo "  make down               - Stop development containers"
	@echo "  make logs               - View all container logs"
	@echo "  make logs-backend       - View backend logs"
	@echo "  make logs-bot           - View bot logs"
	@echo "  make logs-worker        - View worker logs"
	@echo "  make logs-beat          - View beat scheduler logs"
	@echo "  make logs-postgres      - View postgres logs"
	@echo "  make logs-redis         - View redis logs"
	@echo "  make migrate            - Run database migrations"
	@echo "  make shell-backend      - Open backend shell"
	@echo "  make shell-bot          - Open bot shell"
	@echo "  make shell-postgres     - Open postgres CLI"
	@echo "  make test               - Run tests"
	@echo "  make lint               - Run linters"
	@echo "  make format             - Format code"
	@echo ""
	@echo "Production Commands:"
	@echo "  make prod-up            - Start production containers"
	@echo "  make prod-down          - Stop production containers"
	@echo "  make prod-logs          - View production logs"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make backup             - Backup database"
	@echo "  make clean              - Remove volumes and orphaned containers"
	@echo "  make help               - Show this help message"

# Development targets
up:
	$(COMPOSE) up -d
	@echo "✓ Development environment started"

down:
	$(COMPOSE) down
	@echo "✓ Development environment stopped"

logs:
	$(COMPOSE) logs -f

logs-backend:
	$(COMPOSE) logs -f backend

logs-bot:
	$(COMPOSE) logs -f bot

logs-worker:
	$(COMPOSE) logs -f worker

logs-beat:
	$(COMPOSE) logs -f beat

logs-postgres:
	$(COMPOSE) logs -f postgres

logs-redis:
	$(COMPOSE) logs -f redis

migrate:
	$(COMPOSE) exec backend alembic upgrade head
	@echo "✓ Database migrations completed"

shell-backend:
	$(COMPOSE) exec backend /bin/bash

shell-bot:
	$(COMPOSE) exec bot /bin/bash

shell-postgres:
	$(COMPOSE) exec postgres psql -U postgres -d vpn_system

test:
	$(COMPOSE) exec backend pytest -v --cov=. --cov-report=html
	@echo "✓ Tests completed. Coverage report: htmlcov/index.html"

lint:
	$(COMPOSE) exec backend flake8 . --max-line-length=120
	$(COMPOSE) exec backend pylint **/*.py
	@echo "✓ Linting completed"

format:
	$(COMPOSE) exec backend black . --line-length=120
	$(COMPOSE) exec backend isort .
	@echo "✓ Code formatting completed"

# Production targets
prod-up:
	$(PROD_COMPOSE) up -d
	@echo "✓ Production environment started"

prod-down:
	$(PROD_COMPOSE) down
	@echo "✓ Production environment stopped"

prod-logs:
	$(PROD_COMPOSE) logs -f

# Utility targets
backup:
	@bash scripts/backup.sh

clean:
	$(COMPOSE) down -v
	docker system prune -f
	@echo "✓ Cleanup completed"

build-dev:
	$(COMPOSE) build --no-cache

build-prod:
	$(PROD_COMPOSE) build --no-cache

restart:
	$(COMPOSE) restart
	@echo "✓ Containers restarted"

ps:
	$(COMPOSE) ps

stats:
	docker stats --no-stream

db-reset:
	$(COMPOSE) exec postgres dropdb -U postgres -f vpn_system || true
	$(COMPOSE) exec postgres createdb -U postgres vpn_system
	$(COMPOSE) exec backend alembic upgrade head
	@echo "✓ Database reset completed"
