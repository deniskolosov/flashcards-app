.PHONY: help install test test-fast test-coverage test-docker test-clean lint format lint-docker

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
	@echo "  make lint-docker  - Run linting checks in Docker"
	@echo "  make format       - Format code with ruff"
	@echo ""
	@echo "💡 The test database is created automatically - no manual setup required!"

install:
	@echo "📦 Installing dependencies..."
	@uv sync

test:
	@echo "🧪 Running tests with coverage..."
	@echo "   Database will be created automatically if needed"
	@uv run pytest tests/ --cov=backend --cov-report=html --cov-report=term

test-fast:
	@echo "🚀 Running tests (fast mode)..."
	@uv run pytest tests/

test-coverage:
	@echo "📊 Running tests with detailed coverage..."
	@uv run pytest tests/ --cov=backend --cov-report=html --cov-report=term-missing --cov-branch
	@echo ""
	@echo "📋 Coverage report generated:"
	@echo "   • Terminal: above"
	@echo "   • HTML: htmlcov/index.html"

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
	@uv run ruff check .

format:
	@echo "✨ Formatting code..."
	@uv run ruff format .
	@uv run ruff check --fix .

lint-docker:
	@echo "🐳 Running linting checks in Docker..."
	@docker run --rm -v "$(PWD)":/app -w /app python:3.13-slim sh -c "pip install uv && uv sync && uv run ruff check ."

# Convenience aliases
check: lint
fmt: format
tests: test