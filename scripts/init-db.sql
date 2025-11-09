-- Database initialization script for PostgreSQL
-- This script runs when the PostgreSQL container starts for the first time

-- Create additional databases for different environments
CREATE DATABASE flashcards_test;
CREATE DATABASE flashcards_staging;

-- Create a read-only user for production monitoring/debugging
CREATE USER flashcards_readonly WITH PASSWORD 'readonly_password';

-- Grant appropriate permissions
GRANT CONNECT ON DATABASE flashcards_dev TO flashcards_readonly;
GRANT CONNECT ON DATABASE flashcards_test TO flashcards_readonly;
GRANT CONNECT ON DATABASE flashcards_staging TO flashcards_readonly;

-- Switch to the main database to set up schema permissions
\c flashcards_dev;

-- Grant read-only permissions to the readonly user
GRANT USAGE ON SCHEMA public TO flashcards_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO flashcards_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO flashcards_readonly;

-- Create indexes for better performance (these will be managed by Alembic in production)
-- This is just for initial setup if needed

-- Log the completion
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;
