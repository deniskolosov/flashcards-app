"""
Shared pytest fixtures for test database management.
Provides automatic test database creation and cleanup.
"""

import os

import psycopg2
import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text

from backend.database import Database
from backend.models import Base

# Test database configuration
TEST_DB_USER = "flashcards"
TEST_DB_PASSWORD = "test_password"
TEST_DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
TEST_DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
TEST_DB_NAME = "flashcards_test"
TEST_DB_URL = (
    f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-scoped fixture to ensure test database exists.
    Runs once before all tests.
    """
    # Try to create database if it doesn't exist
    try:
        # First try to connect to the test database directly
        try:
            test_conn = psycopg2.connect(
                dbname=TEST_DB_NAME,
                user=TEST_DB_USER,
                password=TEST_DB_PASSWORD,
                host=TEST_DB_HOST,
                port=TEST_DB_PORT,
            )
            test_conn.close()
            print(f"✓ Test database already exists: {TEST_DB_NAME}")
        except psycopg2.OperationalError:
            # Database doesn't exist, try to create it
            try:
                conn = psycopg2.connect(
                    dbname="postgres",
                    user=TEST_DB_USER,
                    password=TEST_DB_PASSWORD,
                    host=TEST_DB_HOST,
                    port=TEST_DB_PORT,
                )
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cursor = conn.cursor()

                # Create database
                cursor.execute(f"CREATE DATABASE {TEST_DB_NAME}")
                print(f"✓ Created test database: {TEST_DB_NAME}")

                cursor.close()
                conn.close()
            except psycopg2.Error:
                # If we can't create database, try with postgres user
                try:
                    conn = psycopg2.connect(
                        dbname="postgres", user="postgres", host=TEST_DB_HOST, port=TEST_DB_PORT
                    )
                    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                    cursor = conn.cursor()

                    # Create user if doesn't exist
                    cursor.execute(f"SELECT 1 FROM pg_roles WHERE rolname = '{TEST_DB_USER}'")
                    if not cursor.fetchone():
                        cursor.execute(
                            f"CREATE USER {TEST_DB_USER} WITH PASSWORD '{TEST_DB_PASSWORD}'"
                        )
                        print(f"✓ Created user: {TEST_DB_USER}")

                    # Create database if doesn't exist
                    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
                    if not cursor.fetchone():
                        cursor.execute(f"CREATE DATABASE {TEST_DB_NAME} OWNER {TEST_DB_USER}")
                        print(f"✓ Created test database: {TEST_DB_NAME}")

                    # Grant privileges
                    cursor.execute(
                        f"GRANT ALL PRIVILEGES ON DATABASE {TEST_DB_NAME} TO {TEST_DB_USER}"
                    )

                    cursor.close()
                    conn.close()
                except psycopg2.Error as e:
                    pytest.exit(
                        f"❌ Cannot create test database. Ensure PostgreSQL is running and accessible.\n"
                        f"   Host: {TEST_DB_HOST}:{TEST_DB_PORT}\n"
                        f"   Error: {e}\n\n"
                        f"   Quick fix: Run 'make test-setup' to create database manually"
                    )

        # Create all tables
        engine = create_engine(TEST_DB_URL)
        Base.metadata.create_all(engine)
        engine.dispose()
        print(f"✓ Test database ready: {TEST_DB_URL}")

    except Exception as e:
        pytest.exit(
            f"❌ Failed to set up test database.\n"
            f"   Ensure PostgreSQL is running on {TEST_DB_HOST}:{TEST_DB_PORT}\n"
            f"   Error: {e}\n\n"
            f"   Try: make test-setup"
        )

    yield

    # Optional: Drop all tables after test session (for complete cleanup)
    # Uncomment if you want fresh schema each run
    # engine = create_engine(TEST_DB_URL)
    # Base.metadata.drop_all(engine)
    # engine.dispose()


@pytest.fixture(autouse=True)
def clean_database():
    """
    Function-scoped fixture to clean all tables before each test.
    Provides test isolation.
    """
    try:
        engine = create_engine(TEST_DB_URL)
        with engine.connect() as conn:
            # Truncate all tables in reverse order to handle foreign keys
            conn.execute(text("TRUNCATE TABLE reviews RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE flashcards RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE decks RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE config RESTART IDENTITY CASCADE"))
            conn.commit()
        engine.dispose()
    except Exception:
        # If truncate fails (e.g., tables don't exist yet), that's okay
        pass

    yield

    # Cleanup happens before next test via autouse


@pytest.fixture
def test_db():
    """
    Provide a clean Database instance for tests.
    This replaces the individual test_db fixtures in test files.
    """
    return Database(TEST_DB_URL)


@pytest.fixture
def db():
    """
    Alias for test_db for backward compatibility.
    Some tests use 'db' fixture name.
    """
    return Database(TEST_DB_URL)
