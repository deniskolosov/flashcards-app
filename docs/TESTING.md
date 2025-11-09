# 🧪 Testing Guide

This guide explains how to run tests in the Flashcard Study App. **No manual database setup is required** - everything is automated!

## Quick Start

```bash
# Fresh repo - just run tests!
git clone <repo>
cd study-cards
uv sync
make test
```

That's it! The test database is created automatically.

## Available Test Commands

### Basic Testing

```bash
make test          # Run all tests with coverage
make test-fast     # Run tests without coverage (faster)
make test-coverage # Detailed coverage report
```

### Docker Testing (Completely Isolated)

```bash
make test-docker   # Run tests in Docker containers
```

### Specific Tests

```bash
# Run specific test file
uv run pytest tests/test_api.py -v

# Run specific test
uv run pytest tests/test_api.py::test_create_deck -v

# Run with pattern
uv run pytest -k "test_deck" -v
```

### Development Commands

```bash
make lint     # Run linting checks
make format   # Format code
make install  # Install dependencies
```

## Test Database Architecture

### Automatic Setup ✨

The test system automatically:

1. **Creates test database** (`flashcards_test`) if it doesn't exist
2. **Creates test user** (`flashcards`) with proper permissions
3. **Creates tables** using SQLAlchemy schema
4. **Cleans tables** between tests for isolation
5. **Provides helpful errors** if PostgreSQL isn't running

### Database Details

- **Host**: `localhost:5432` (local) or `postgres-test:5432` (Docker)
- **Database**: `flashcards_test`
- **User**: `flashcards` / Password: `test_password`
- **URL**: `postgresql://flashcards:test_password@localhost:5432/flashcards_test`

### Test Isolation 🔒

Each test gets a **clean database state**:
- Tables are truncated (not dropped) between tests
- Fast cleanup using `TRUNCATE ... CASCADE`
- No test data persists between runs
- Parallel test execution is safe

## Troubleshooting

### Common Issues

#### ❌ "Cannot connect to PostgreSQL"

**Problem**: PostgreSQL isn't running

**Solutions**:
```bash
# macOS (Homebrew)
brew services start postgresql

# Check if running
pg_isready

# Check what's on port 5432
lsof -i :5432
```

#### ❌ "role 'flashcards' does not exist"

**Problem**: Test user doesn't exist

**Solution**: Tests will auto-create the user, but if you have connection issues:
```bash
# Connect as postgres user and create test setup manually
psql -U postgres -c "CREATE USER flashcards WITH PASSWORD 'test_password';"
psql -U postgres -c "CREATE DATABASE flashcards_test OWNER flashcards;"
```

#### ❌ "permission denied for schema public"

**Problem**: User permissions issue

**Solution**:
```bash
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE flashcards_test TO flashcards;"
psql -U postgres -d flashcards_test -c "GRANT ALL ON SCHEMA public TO flashcards;"
```

#### ❌ Tests fail randomly

**Problem**: Database state issues

**Solutions**:
```bash
# Clean test database completely
make test-clean

# Or restart from scratch
psql -U postgres -c "DROP DATABASE IF EXISTS flashcards_test;"
make test  # Will recreate automatically
```

### Docker Issues

#### ❌ "docker-compose command not found"

**Solutions**:
```bash
# Install Docker Desktop (includes docker-compose)
# Or install docker-compose separately
pip install docker-compose
```

#### ❌ Docker tests are slow

**Solutions**:
```bash
# Use local testing instead (much faster)
make test

# Or enable Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1
make test-docker
```

### Performance Tips

#### Faster Local Testing 🚀

```bash
# Skip coverage for speed during development
make test-fast

# Run specific tests
uv run pytest tests/test_api.py

# Parallel testing (if you have pytest-xdist)
uv run pytest -n auto
```

#### Optimal Development Workflow

```bash
# 1. Install dependencies once
make install

# 2. Run specific tests while developing
uv run pytest tests/test_api.py::test_create_deck -v

# 3. Run full test suite before committing
make test

# 4. Check linting
make lint
```

## Test Structure

### Test Files

```
tests/
├── conftest.py                           # Shared fixtures & database setup
├── test_api.py                          # FastAPI endpoint tests
├── test_database.py                     # Database DAO tests
├── test_spaced_repetition_api.py        # Spaced repetition API tests
├── test_spaced_repetition_integration.py # SR integration tests
├── test_grading.py                      # AI grading tests
├── test_parser.py                       # Content parser tests
└── test_spaced_repetition.py            # SR algorithm tests
```

### Key Files

- **`conftest.py`**: Auto-creates test database, provides clean fixtures
- **`pyproject.toml`**: pytest configuration
- **`docker-compose.test.yml`**: Isolated Docker test environment

### Test Categories

Tests are marked for easy filtering:

```bash
# Run only unit tests (fast)
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"
```

## Environment Variables

### Local Testing

The test system uses these defaults:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=flashcards_test
POSTGRES_USER=flashcards
POSTGRES_PASSWORD=test_password
```

### Docker Testing

Docker overrides these for container networking:
```bash
POSTGRES_HOST=postgres-test
POSTGRES_PORT=5432
# (other settings same)
```

### Custom Configuration

Override for different setups:
```bash
# Use different PostgreSQL instance
export POSTGRES_HOST=my-pg-server
export POSTGRES_PORT=5433
make test
```

## Coverage Reports

### Viewing Coverage

```bash
# Run tests with coverage
make test-coverage

# Open HTML report
open htmlcov/index.html
```

### Coverage Goals

- **Overall**: 90%+ coverage
- **Critical paths**: 100% (database, API endpoints)
- **Utilities**: 80%+ coverage

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Pull requests
- Pushes to main branch

The CI uses the same PostgreSQL setup as local testing.

### Local CI Simulation

```bash
# Simulate CI environment
make test-docker
```

## Writing Tests

### Basic Test Structure

```python
def test_my_feature(db):
    """Test description."""
    # db fixture provides clean database
    # Tables are automatically cleaned between tests

    # Your test code here
    assert result == expected
```

### Using Fixtures

```python
def test_with_data(deck_dao, test_db):
    """Test with DAO."""
    # Use existing DAO fixtures
    deck = deck_dao.create(DeckCreate(name="Test"))
    assert deck.id is not None
```

### Test Isolation

```python
def test_isolation_1(db):
    # Create some data
    deck = DeckDAO(db).create(DeckCreate(name="Test"))

def test_isolation_2(db):
    # Previous test data is gone automatically
    decks = DeckDAO(db).get_all()
    assert len(decks) == 0  # Clean slate
```

## Advanced Topics

### Custom Test Database

```python
# In your test file
@pytest.fixture
def custom_db():
    return Database("postgresql://custom:password@localhost:5432/custom_db")
```

### Test Performance

- **Table truncation**: ~1ms per test
- **Full rebuild**: ~100ms (not used)
- **Docker startup**: ~10s (one-time)

### Debugging Tests

```bash
# Run with output
uv run pytest tests/test_api.py -s -v

# Debug specific test
uv run pytest tests/test_api.py::test_create_deck -s -v --tb=long

# Run with debugger
uv run pytest tests/test_api.py::test_create_deck --pdb
```

---

## 🎯 Summary

- **Zero setup**: Tests auto-create database
- **Fast isolation**: Table truncation between tests
- **Flexible**: Local PostgreSQL or Docker containers
- **Comprehensive**: 129 tests with coverage reporting
- **Developer friendly**: Clear errors and documentation

The testing system is designed to "just work" for developers while providing comprehensive coverage and isolation. Happy testing! 🚀
