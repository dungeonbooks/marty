# Marty - AI Bookstore Chatbot Justfile
# Just is a command runner: https://github.com/casey/just
#
# To enable parallel CI steps, install GNU parallel:
#   sudo apt-get update && sudo apt-get install -y parallel

# Show available commands
default:
    @just --list

# Install all dependencies using uv
install:
    uv sync

# Install dependencies including development tools
install-dev:
    uv sync --group dev

# Add a production dependency
add package:
    uv add {{package}}

# Add a development dependency
add-dev package:
    uv add --group dev {{package}}

# Start development server with hot reload
dev: test-infra-up
    uv run fastapi dev src/main.py

# Start production server
run:
    uv run python src/main.py

# Run all tests
test:
    uv run pytest

# Run tests with verbose output
test-verbose:
    uv run pytest -v

# Run specific test file
test-file file:
    uv run pytest tests/{{file}}

# Run tests with coverage report
test-cov:
    uv run pytest --cov=. --cov-report=html

# Format code with ruff
format:
    uv run ruff format src scripts tests

# Lint code with ruff
lint:
    uv run ruff check src scripts tests

# Check formatting without rewriting files (CI runs this; `just format` mutates)
format-check:
    uv run ruff format --check src scripts tests

# Auto-fix linting issues
lint-fix:
    uv run ruff check --fix src scripts tests

# Bandit security scan
bandit:
    uv run bandit -r src

# Type check with ty
check:
    uv run ty check src

# Run format and lint checks
check-all:
    just format
    just lint
    just check

# Apply database migrations
db-migrate:
    uv run alembic upgrade head

# Rollback last migration
db-rollback:
    uv run alembic downgrade -1

# Reset database to base and reapply all migrations
db-reset:
    uv run alembic downgrade base
    uv run alembic upgrade head

# Generate new migration
db-revision message:
    uv run alembic revision --autogenerate -m "{{message}}"

# Start interactive chat with Marty (internal testing)
chat:
    uv run python scripts/chat.py

# Test SMS functionality with real API calls (internal testing)
sms:
    uv run python scripts/sms.py

# Run comprehensive integration test (costs money)
smoke-test:
    uv run python scripts/smoke_test.py

# Test database connection
test-db:
    uv run python src/database.py

# Start test infrastructure (PostgreSQL + Redis for testing)
test-infra-up:
    docker-compose -f docker-compose.test.yml up -d

# Stop test infrastructure
test-infra-down:
    docker-compose -f docker-compose.test.yml down -v

# Run all tests with test infra
test-all: test-infra-up
    TEST_DATABASE_URL=postgresql://marty_test:password@localhost:5432/marty_test TEST_REDIS_URL=redis://localhost:6379 uv run pytest
    just test-infra-down

# Complete project setup
setup: install-dev pre-commit-install
    @echo "Setting up Marty project..."
    @echo "Setup complete! Don't forget to:"
    @echo "1. Copy .env.example to .env"
    @echo "2. Add your API keys to .env"
    @echo "3. Run 'just db-migrate' to setup database"

# Create .env file from example
setup-env:
    cp .env.example .env
    @echo "Created .env file. Please edit with your API keys."

# Install pre-commit hooks
pre-commit-install:
    uv run pre-commit install

# Run pre-commit on all files
pre-commit-run:
    uv run pre-commit run --all-files

# Clean up generated files
clean:
    rm -rf .pytest_cache
    rm -rf .ruff_cache
    rm -rf htmlcov
    rm -rf .coverage
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete

# Check system health
health:
    @echo "Testing database connection..."
    just test-db
    @echo "Running basic tests..."
    just test

# Show detailed help for all commands
help:
    @echo "Marty - AI Bookstore Chatbot"
    @echo ""
    @echo "Development:"
    @echo "  just dev          - Start development server"
    @echo "  just run          - Start production server"
    @echo "  just chat         - Interactive chat testing"
    @echo "  just sms          - Test SMS functionality (⚠️ uses real API)"
    @echo ""
    @echo "Testing:"
    @echo "  just test         - Run all tests"
    @echo "  just test-cov     - Run tests with coverage"
    @echo "  just smoke-test   - Integration test (⚠️ costs money)"
    @echo ""
    @echo "Code Quality:"
    @echo "  just format       - Format code"
    @echo "  just lint         - Lint code"
    @echo "  just format-check - Check formatting without rewriting"
    @echo "  just check        - Type check with ty"
    @echo "  just check-all    - Format, lint, and type check"
    @echo ""
    @echo "Database:"
    @echo "  just db-migrate   - Apply migrations"
    @echo "  just db-reset     - Reset database"
    @echo "  just db-revision  - Create new migration"
    @echo ""
    @echo "Dependencies:"
    @echo "  just install      - Install dependencies"
    @echo "  just install-dev  - Install with dev tools"
    @echo "  just add          - Add production dependency"
    @echo "  just add-dev      - Add development dependency"

# Run lint, type check, and unit tests (fast, no infra)
ci:
    parallel --jobs $(nproc) ::: "just lint" "just format-check" "just check" "just bandit"
    uv run pytest -m "not integration"

# Run lint, type check, and all tests (with infra)
ci-full:
    parallel --jobs $(nproc) ::: "just lint" "just format-check" "just check" "just bandit"
    just test-all

# Run only integration tests (requires test infra)
test-integration: test-infra-up
    TEST_DATABASE_URL=postgresql://marty_test:password@localhost:5432/marty_test TEST_REDIS_URL=redis://localhost:6379 uv run pytest -m integration
    just test-infra-down

# Watch for changes and restart development server
watch:
    find . -name "*.py" | entr -r just dev
