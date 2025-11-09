# Docker Setup Guide

This guide explains how to run the Flashcard Study App using Docker with PostgreSQL.

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- `.env` file with your API keys (copy from `.env.example`)

### Development (Default)
```bash
# Start all services (app + PostgreSQL)
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f app
docker-compose logs -f postgres
```

The application will be available at:
- **App**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:5050 (admin@flashcards.local / admin_password)

### With Database Management Tools
```bash
# Start with pgAdmin included
docker-compose --profile tools up

# Or start pgAdmin separately
docker-compose up postgres app
docker-compose up pgadmin
```

## Environment Configurations

### Development (Default)
- Auto-reload enabled for code changes
- Source code mounted as volumes
- Full logging and debugging
- PostgreSQL exposed on port 5432

```bash
docker-compose up
```

### Staging
- Production-like environment for testing
- No auto-reload, optimized performance
- pgAdmin available for debugging

```bash
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up
```

### Production
- Optimized for performance and security
- Multiple workers, resource limits
- No development tools or port exposure
- Requires environment variables for secrets

```bash
docker-compose -f docker-compose.yml -f docker-compose.production.yml up
```

## Database Management

### Connecting to PostgreSQL

**From Host Machine:**
```bash
# Development
psql -h localhost -p 5432 -U flashcards -d flashcards_dev

# Via Docker
docker-compose exec postgres psql -U flashcards -d flashcards_dev
```

**Connection Strings:**
```bash
# Development
DATABASE_URL=postgresql://flashcards:flashcards_dev_password@localhost:5432/flashcards_dev

# Staging
DATABASE_URL=postgresql://flashcards_staging:flashcards_staging_password@localhost:5432/flashcards_staging

# Production (within Docker network)
DATABASE_URL=postgresql://flashcards_prod:${POSTGRES_PASSWORD}@postgres:5432/flashcards_prod
```

### Running Migrations

```bash
# Run migrations against local PostgreSQL
DATABASE_URL=postgresql://flashcards:flashcards_dev_password@localhost:5432/flashcards_dev \
uv run alembic upgrade head

# Or within the container
docker-compose exec app alembic upgrade head
```

### Backup and Restore

```bash
# Backup
docker-compose exec postgres pg_dump -U flashcards flashcards_dev > backup.sql

# Restore
docker-compose exec -T postgres psql -U flashcards flashcards_dev < backup.sql
```

## Environment Switching

You can point your local app to different database environments:

### Local App → Staging Database
```bash
# Start local app with staging database
DATABASE_URL=postgresql://staging-user:password@staging-host:5432/flashcards_staging \
uv run uvicorn backend.main:app --reload
```

### Local App → Production Database (Read-Only)
```bash
# Use read-only credentials for safety
DATABASE_URL=postgresql://flashcards_readonly:readonly_password@prod-host:5432/flashcards_prod \
uv run uvicorn backend.main:app --reload
```

## Docker Commands Reference

### Container Management
```bash
# Start services
docker-compose up [service_name]

# Stop services
docker-compose down

# Restart a service
docker-compose restart app

# View running containers
docker-compose ps

# Execute command in container
docker-compose exec app bash
docker-compose exec postgres psql -U flashcards flashcards_dev
```

### Logs and Debugging
```bash
# View logs
docker-compose logs -f [service_name]

# Debug container
docker-compose exec app bash

# Check container health
docker-compose ps
docker inspect flashcard-app | grep Health
```

### Data Management
```bash
# Remove all data (destructive!)
docker-compose down -v

# Remove just containers, keep data
docker-compose down

# Rebuild containers
docker-compose build [service_name]
docker-compose up --build
```

## Volume Management

### Persistent Data
- `postgres_data`: PostgreSQL database files
- `pgadmin_data`: pgAdmin configuration and connections
- `./logs`: Application logs (mounted from host)

### Development Volumes
- `./backend`: Python backend code (read-only mount)
- `./frontend`: Frontend assets (read-only mount)
- `./alembic`: Database migrations (read-only mount)

## Troubleshooting

### Common Issues

**PostgreSQL Connection Failed:**
```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U flashcards

# View PostgreSQL logs
docker-compose logs postgres
```

**App Won't Start:**
```bash
# Check environment variables
docker-compose exec app printenv | grep DATABASE_URL

# Run migrations manually
docker-compose exec app alembic upgrade head

# Check app logs
docker-compose logs app
```

**Port Already in Use:**
```bash
# Change ports in docker-compose.yml or stop conflicting services
sudo lsof -i :8000
sudo lsof -i :5432
```

### Reset Everything
```bash
# Nuclear option: remove all containers, volumes, and networks
docker-compose down -v --remove-orphans
docker system prune -f
docker volume prune -f
```

## Production Deployment

### Environment Variables Required
```bash
# Required for production
POSTGRES_PASSWORD=your_secure_password
ANTHROPIC_API_KEY=sk-ant-your-key
OPENAI_API_KEY=sk-your-key
DEFAULT_AI_PROVIDER=anthropic
```

### Security Considerations
- PostgreSQL not exposed on host ports
- Separate production passwords
- Resource limits configured
- No development tools included

### Health Checks
Both services include health checks:
- **PostgreSQL**: `pg_isready` check
- **FastAPI**: HTTP health endpoint check

Monitor with:
```bash
docker-compose ps
docker inspect flashcard-app | grep -A 5 Health
```

## Next Steps

After setting up Docker:
1. Run database migrations: `docker-compose exec app alembic upgrade head`
2. Import sample flashcards: Visit http://localhost:8000 and use the import feature
3. Test the application with both AI providers
4. Set up GitHub Actions for automated testing and deployment
