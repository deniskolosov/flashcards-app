.PHONY: help install test test-fast test-coverage test-docker test-clean lint format lint-docker type-check pre-commit-install pre-commit-run pre-commit-all migrate-test migrate-up migrate-down migrate-check

help:
	@echo "📋 Available commands:"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test         - Run all tests (auto-creates test DB)"
	@echo "  make test-fast    - Run tests without coverage"
	@echo "  make test-coverage - Run tests with detailed coverage report"
	@echo "  make test-docker  - Run tests in Docker (completely isolated)"
	@echo "  make test-clean   - Clean test database"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make install      - Install all dependencies"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with ruff"
	@echo "  make type-check   - Run type checking with mypy"
	@echo "  make lint-docker  - Run linting checks in Docker"
	@echo ""
	@echo "🪝 Pre-commit Hooks:"
	@echo "  make pre-commit-install - Install pre-commit hooks"
	@echo "  make pre-commit-run     - Run pre-commit on staged files"
	@echo "  make pre-commit-all     - Run pre-commit on all files"
	@echo ""
	@echo "🗄️ Database Migrations:"
	@echo "  make migrate-up         - Apply all migrations"
	@echo "  make migrate-down       - Rollback one migration"
	@echo "  make migrate-check      - Check migration status"
	@echo "  make migrate-test       - Test migrations (requires clean DB)"
	@echo ""
	@echo "💡 The test database is created automatically - no manual setup required!"

install:
	@echo "📦 Installing dependencies..."
	@uv sync

test:
	@echo "🧪 Running tests with coverage..."
	@echo "   Database will be created automatically if needed"
	@uv run pytest tests/ --cov=backend --cov-report=html --cov-report=term --cov-fail-under=85

test-fast:
	@echo "🚀 Running tests (fast mode)..."
	@uv run pytest tests/

test-coverage:
	@echo "📊 Running tests with detailed coverage..."
	@uv run pytest tests/ --cov=backend --cov-report=html --cov-report=term-missing --cov-branch --cov-fail-under=85
	@echo ""
	@echo "📋 Coverage report generated:"
	@echo "   • Terminal: above"
	@echo "   • HTML: htmlcov/index.html"
	@echo ""
	@echo "⚠️  Coverage threshold: 85% minimum required"

test-docker:
	@echo "🐳 Running tests in Docker..."
	@echo "   This provides complete isolation from your local environment"
	@docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
	@docker compose -f docker-compose.test.yml down

test-clean:
	@echo "🧹 Cleaning test database..."
	@uv run python -c "from sqlalchemy import create_engine, text; from backend.models import Base; engine = create_engine('postgresql://flashcards:test_password@localhost:5432/flashcards_test'); conn = engine.connect(); conn.execute(text('DROP SCHEMA public CASCADE')); conn.execute(text('CREATE SCHEMA public')); conn.close(); print('✓ Test database cleaned')" 2>/dev/null || echo "⚠️  Test database not found (this is fine)"

lint:
	@echo "🔍 Running linting checks..."
	@echo "  → Running ruff linting..."
	@uv run ruff check .
	@echo "  → Checking code formatting..."
	@uv run ruff format --check .
	@echo "  → Checking import ordering..."
	@uv run ruff check --select I .
	@echo "✅ All linting checks passed!"

format:
	@echo "✨ Formatting code..."
	@uv run ruff format .
	@uv run ruff check --fix .

type-check:
	@echo "🔍 Running type checking..."
	@uv run mypy

lint-docker:
	@echo "🐳 Running linting checks in Docker..."
	@docker run --rm -v "$(PWD)":/app -w /app python:3.13-slim sh -c "pip install uv && uv sync && uv run ruff check ."

pre-commit-install:
	@echo "🪝 Installing pre-commit hooks..."
	@uv run pre-commit install
	@uv run pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed! They will run automatically on git commit."

pre-commit-run:
	@echo "🪝 Running pre-commit on staged files..."
	@uv run pre-commit run

pre-commit-all:
	@echo "🪝 Running pre-commit on all files..."
	@uv run pre-commit run --all-files

migrate-up:
	@echo "🔄 Applying database migrations..."
	@uv run alembic upgrade head
	@echo "✅ Migrations applied successfully"

migrate-down:
	@echo "🔄 Rolling back one migration..."
	@uv run alembic downgrade -1
	@echo "✅ Migration rolled back successfully"

migrate-check:
	@echo "🔍 Checking migration status..."
	@uv run alembic current
	@uv run alembic history

migrate-test:
	@echo "🧪 Testing database migrations..."
	@echo "⚠️  This will test migrations on a clean database"
	@echo "   Make sure you have a test database configured"
	@echo ""
	@echo "Testing fresh migration..."
	@uv run alembic upgrade head
	@echo ""
	@echo "Testing schema validation..."
	@uv run python -c "\
	from backend.database import Database; \
	from sqlalchemy import inspect; \
	db = Database(); \
	inspector = inspect(db.engine); \
	tables = inspector.get_table_names(); \
	expected = ['alembic_version', 'decks', 'flashcards', 'reviews', 'config']; \
	for table in expected: \
		assert table in tables, f'Missing table: {table}'; \
		print(f'✅ Table {table} exists'); \
	print('✅ Migration test completed successfully')"

# Convenience aliases
check: lint
fmt: format
tests: test
hooks: pre-commit-run
migrate: migrate-up
