.PHONY: help install install-dev setup-env dev run test test-unit test-contract test-integration test-cov \
        lint lint-fix format format-check security typecheck pre-commit-install pre-commit-run \
        docker-build docker-run docker-up docker-down docker-logs db-setup clean clean-all check ci

# Variables
PYTHON := python
PYTEST := pytest
RUFF := ruff
UVICORN := uvicorn
APP := deduptickets.main:app
PORT := 8000

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo.
	@echo Usage: make [target]
	@echo.
	@echo Targets:
	@echo   install             Install production dependencies
	@echo   install-dev         Install with development dependencies
	@echo   setup-env           Copy .env.example to .env
	@echo   dev                 Run development server with auto-reload
	@echo   run                 Run production-like server
	@echo   test                Run all tests
	@echo   test-unit           Run unit tests only
	@echo   test-contract       Run contract tests only
	@echo   test-integration    Run integration tests only
	@echo   test-cov            Run tests with coverage report
	@echo   lint                Check code with ruff linter
	@echo   lint-fix            Fix linting issues automatically
	@echo   format              Format code with ruff
	@echo   format-check        Check code formatting without changes
	@echo   security            Run bandit security scan
	@echo   typecheck           Run mypy type checking
	@echo   pre-commit-install  Install pre-commit hooks
	@echo   pre-commit-run      Run pre-commit on all files
	@echo   docker-build        Build Docker image
	@echo   docker-run          Run Docker container
	@echo   docker-up           Start all services with docker-compose
	@echo   docker-down         Stop all docker-compose services
	@echo   docker-logs         Follow backend logs from docker-compose
	@echo   db-setup            Initialize Cosmos DB containers
	@echo   clean               Remove build artifacts and caches
	@echo   clean-all           Remove all artifacts including venv
	@echo   check               Run lint, format check, and tests
	@echo   ci                  Run full CI pipeline

##@ Installation

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install with development dependencies
	pip install -e ".[dev]"

setup-env: ## Copy .env.example to .env
	$(PYTHON) -c "import shutil; shutil.copy('.env.example', '.env')"

##@ Development Server

dev: ## Run development server with auto-reload
	$(UVICORN) $(APP) --reload --port $(PORT)

run: ## Run production-like server
	$(UVICORN) $(APP) --host 0.0.0.0 --port $(PORT)

##@ Testing

test: ## Run all tests
	$(PYTEST)

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -m unit

test-contract: ## Run contract tests only
	$(PYTEST) tests/contract/ -m contract

test-integration: ## Run integration tests only
	$(PYTEST) tests/integration/ -m integration

test-cov: ## Run tests with coverage report
	$(PYTEST) --cov=src/deduptickets --cov-report=html --cov-report=term

##@ Code Quality

lint: ## Check code with ruff linter
	$(RUFF) check .

lint-fix: ## Fix linting issues automatically
	$(RUFF) check --fix .

format: ## Format code with ruff
	$(RUFF) format .

format-check: ## Check code formatting without changes
	$(RUFF) format --check .

security: ## Run bandit security scan
	bandit -r src/

typecheck: ## Run mypy type checking
	mypy src/

##@ Pre-commit

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files

##@ Docker

docker-build: ## Build Docker image
	docker build -t deduptickets-backend .

docker-run: ## Run Docker container
	docker run -p $(PORT):$(PORT) --env-file .env deduptickets-backend

docker-up: ## Start all services with docker-compose
	cd .. && docker-compose up -d

docker-down: ## Stop all docker-compose services
	cd .. && docker-compose down

docker-logs: ## Follow backend logs from docker-compose
	cd .. && docker-compose logs -f backend

##@ Database

db-setup: ## Initialize Cosmos DB containers
	$(PYTHON) -m deduptickets.cosmos.setup

##@ Utilities

clean: ## Remove build artifacts and caches
	$(PYTHON) -c "import shutil; import pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.ruff_cache', '.mypy_cache', 'htmlcov']]; pathlib.Path('.coverage').unlink(missing_ok=True)"
	$(PYTHON) -c "import shutil; import pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"

clean-all: clean ## Remove all artifacts including virtual environment
	$(PYTHON) -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"

check: lint format-check test ## Run lint, format check, and tests

ci: lint format-check security typecheck test-cov ## Run full CI pipeline
