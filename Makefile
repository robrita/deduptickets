.PHONY: help install install-dev setup-env dev run test test-unit test-contract test-integration test-cov \
        lint lint-fix format format-check security typecheck pre-commit-install pre-commit-run \
	db-setup generate-data load-data load-ticket migrate-sample-data clean clean-all check ci \
	deploy

# Variables
PYTHON := python
PYTEST := pytest
RUFF := ruff
UVICORN := uvicorn
APP := main:app
PORT := 8000
export PYTHONPATH := backend/src

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
	@echo   db-setup            Initialize Cosmos DB containers
	@echo   generate-data       Generate sample tickets dataset (camelCase)
	@echo   load-data           Load sample tickets via API (COUNT required)
	@echo   load-ticket         Load a single ticket via API (TICKET required)
	@echo   load-batch          Load tickets from a JSON batch file (BATCH required)
	@echo   migrate-sample-data Remove region/city fields and normalize pk to YYYY-MM
	@echo   assign-cosmos-role  Assign Cosmos DB data-plane role for Entra ID auth
	@echo   deploy              Deploy to Azure Functions (APP_NAME required)
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
# 	$(UVICORN) $(APP) --reload --port $(PORT)
	$(UVICORN) $(APP) --port $(PORT)

run: ## Run production-like server
	$(UVICORN) $(APP) --host 0.0.0.0 --port $(PORT)

##@ Testing

test: ## Run all tests
	$(PYTEST)

test-unit: ## Run unit tests only
	$(PYTEST) backend/tests/unit/ -m unit

test-contract: ## Run contract tests only
	$(PYTEST) backend/tests/contract/ -m contract

test-integration: ## Run integration tests only
	$(PYTEST) backend/tests/integration/ -m integration

test-cov: ## Run tests with coverage report
	$(PYTEST) --cov=backend/src --cov-report=html --cov-report=term

##@ Code Quality

lint: ## Check code with ruff linter
	$(RUFF) check backend/

lint-fix: ## Fix linting issues automatically
	$(RUFF) check --fix backend/

format: ## Format code with ruff
	$(RUFF) format backend/

format-check: ## Check code formatting without changes
	$(RUFF) format --check backend/

security: ## Run bandit security scan
	bandit -r backend/src/

typecheck: ## Run mypy type checking
	mypy backend/src/

##@ Pre-commit

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files

##@ Database

db-setup: ## Initialize Cosmos DB containers
	$(PYTHON) -m cosmos.setup

load-data: ## Load sample tickets via API with full dedup pipeline (COUNT required, e.g., make load-data COUNT=50)
ifndef COUNT
	$(error COUNT is required. Usage: make load-data COUNT=50)
endif
	$(PYTHON) backend/scripts/load_tickets.py --count $(COUNT)

load-ticket: ## Load a single ticket via API with full dedup pipeline (TICKET required, e.g., make load-ticket TICKET="#100001")
ifndef TICKET
	$(error TICKET is required. Usage: make load-ticket TICKET="#100001")
endif
	$(PYTHON) backend/scripts/load_tickets.py --ticket-number "$(TICKET)"

load-batch: ## Load tickets from a JSON batch file (BATCH required, e.g., make load-batch BATCH=batch.json)
ifndef BATCH
	$(error BATCH is required. Usage: make load-batch BATCH=./backend/data/batch.json)
endif
	$(PYTHON) backend/scripts/load_tickets.py --batch-file "$(BATCH)"

generate-data: ## Generate sample tickets dataset (camelCase output)
	$(PYTHON) backend/scripts/generate_sample_tickets.py

migrate-sample-data: ## Remove region/city fields and normalize sample ticket pk to YYYY-MM
	$(PYTHON) backend/scripts/migrate_sample_tickets_remove_region_city.py --in-place

assign-cosmos-role: ## Assign Cosmos DB Data Contributor role for Entra ID auth (reads from .env automatically)
	bash scripts/assign_cosmos_role.sh --role contributor

##@ Deployment

deploy: ## Deploy to Azure Functions (APP_NAME required, e.g., make deploy APP_NAME=my-func-app)
ifndef APP_NAME
	$(error APP_NAME is required. Usage: make deploy APP_NAME=my-func-app)
endif
	func azure functionapp publish $(APP_NAME) --python --build remote

##@ Frontend

frontend-lint: ## Lint frontend with ESLint
	cd frontend && npm run lint

frontend-lint-fix: ## Fix ESLint issues automatically
	cd frontend && npm run lint:fix

frontend-format: ## Format frontend with Prettier
	cd frontend && npm run format

frontend-format-check: ## Check frontend formatting
	cd frontend && npm run format:check

frontend-build: ## Build frontend (tsc + vite)
	cd frontend && npm run build

frontend-test: ## Run frontend unit tests (Vitest)
	cd frontend && npm run test

frontend-test-e2e: ## Run frontend E2E tests (Playwright)
	cd frontend && npm run test:e2e

frontend-check: frontend-lint frontend-format-check frontend-build frontend-test ## Run all frontend checks

frontend-ci: frontend-lint frontend-format-check frontend-build frontend-test ## Run full frontend CI pipeline

##@ Documentation

lint-docs: ## Validate AGENTS.md structure and doc links
	$(PYTHON) scripts/lint_docs.py

##@ Utilities

clean: ## Remove build artifacts and caches
	$(PYTHON) -c "import shutil; import pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.ruff_cache', '.mypy_cache', 'htmlcov', 'backend/.pytest_cache', 'backend/.ruff_cache']]; pathlib.Path('.coverage').unlink(missing_ok=True)"
	$(PYTHON) -c "import shutil; import pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"

clean-all: clean ## Remove all artifacts including virtual environment
	$(PYTHON) -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"

check: lint format-check test ## Run lint, format check, and tests

ci: lint format-check security typecheck test-cov lint-docs frontend-ci ## Run full CI pipeline
