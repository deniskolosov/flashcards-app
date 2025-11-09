# Environment Configuration Guide

This guide explains how to configure the Flashcard Study App for different environments.

## Quick Start

### 1. Copy Environment Template
```bash
# For development
cp .env.example .env

# Or use the setup utility
python scripts/setup-env.py list
python scripts/setup-env.py use development
```

### 2. Set Your API Keys
Edit `.env` and add your API keys:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
```

### 3. Validate Configuration
```bash
python scripts/setup-env.py validate
```

## Available Environments

### Development (`.env.development`)
- **Purpose**: Local development with hot reload
- **Database**: PostgreSQL (via Docker)
- **Debug**: Enabled
- **API Docs**: Available at `/docs`
- **CORS**: Permissive for local development

```bash
python scripts/setup-env.py use development
```

### Docker (`.env.docker`)
- **Purpose**: Running in Docker containers
- **Database**: PostgreSQL service in docker-compose
- **Debug**: Enabled
- **Networking**: Container-optimized

```bash
python scripts/setup-env.py use docker
```

### Staging (`.env.staging`)
- **Purpose**: Pre-production testing
- **Database**: Staging PostgreSQL instance
- **Debug**: Disabled
- **Security**: Production-like settings
- **Monitoring**: Enabled

```bash
python scripts/setup-env.py use staging
```

### Production (`.env.production`)
- **Purpose**: Live production deployment
- **Database**: Production PostgreSQL
- **Debug**: Disabled
- **Security**: Maximum security settings
- **Performance**: Optimized for scale

```bash
python scripts/setup-env.py use production
# Or set up interactively:
python scripts/setup-env.py setup-prod
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | `sk-ant-api03-xxx` |
| `OPENAI_API_KEY` | OpenAI GPT API key | `sk-xxx` |
| `DEFAULT_AI_PROVIDER` | Default AI provider | `anthropic` or `openai` |

### Application Settings

| Variable | Description | Default | Environments |
|----------|-------------|---------|--------------|
| `ENVIRONMENT` | Environment name | `development` | All |
| `DEBUG` | Enable debug mode | `false` | Development |
| `LOG_LEVEL` | Logging level | `INFO` | All |
| `HOST` | Server host | `0.0.0.0` | Docker |
| `PORT` | Server port | `8000` | All |

### AI Model Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_MODEL` | Claude model version | `claude-sonnet-4-20250514` |
| `OPENAI_MODEL` | OpenAI model version | `gpt-4o` |

### Security Settings

| Variable | Description | Default | Environment |
|----------|-------------|---------|-------------|
| `SESSION_SECRET` | Session encryption key | Required | Production |
| `CORS_ORIGINS` | Allowed CORS origins | `[]` | All |
| `HTTPS_ONLY` | Force HTTPS | `false` | Production |
| `SECURE_COOKIES` | Secure cookie flag | `false` | Production |
| `HSTS_MAX_AGE` | HSTS header value | `31536000` | Production |

### Performance Settings

| Variable | Description | Default | Environment |
|----------|-------------|---------|-------------|
| `MAX_WORKERS` | Uvicorn workers | `1` | Production |
| `MAX_CONNECTIONS` | DB connection pool | `10` | All |
| `WORKER_TIMEOUT` | Worker timeout (sec) | `30` | Production |

### Feature Flags

| Variable | Description | Default | Environment |
|----------|-------------|---------|-------------|
| `ENABLE_REGISTRATION` | User registration | `true` | Development |
| `ENABLE_DEMO_MODE` | Demo features | `true` | Development |
| `ENABLE_API_DOCS` | FastAPI docs | `true` | Development |
| `ENABLE_RATE_LIMITING` | API rate limiting | `false` | Production |

### Monitoring & Observability

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_METRICS` | Metrics collection | `false` |
| `SENTRY_DSN` | Sentry error tracking | Optional |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `60` |

## Environment Setup Utility

The `scripts/setup-env.py` utility helps manage environment configurations:

### Commands

```bash
# List available environments
python scripts/setup-env.py list

# Switch to an environment
python scripts/setup-env.py use development
python scripts/setup-env.py use staging --force

# Validate current configuration
python scripts/setup-env.py validate

# Get environment info
python scripts/setup-env.py info production

# Interactive production setup
python scripts/setup-env.py setup-prod
```

### Validation Features

The utility validates:
- ✅ Required variables are present
- 🔒 No insecure default values
- ⚠️ Environment-specific warnings
- 📋 Configuration completeness

## Database Configuration

### Local Development
```bash
# Use Docker PostgreSQL
DATABASE_URL=postgresql://flashcards:flashcards_dev_password@localhost:5432/flashcards_dev
```

### Production
```bash
# Use environment variable (recommended)
DATABASE_URL=${DATABASE_URL}

# Or direct connection
DATABASE_URL=postgresql://prod_user:secure_password@prod-db.example.com:5432/flashcards_prod
```

### Connection Pool Settings
The app uses PostgreSQL with optimized connection pooling:

- **PostgreSQL**: QueuePool with 10 connections, 20 overflow

## AI Provider Configuration

### Anthropic Claude
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514
DEFAULT_AI_PROVIDER=anthropic
```

### OpenAI GPT
```bash
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o
DEFAULT_AI_PROVIDER=openai
```

### Both Providers
Users can switch between providers in the app settings, even if you configure both.

## Security Best Practices

### 🔒 Production Security Checklist

- [ ] Use strong, unique `SESSION_SECRET` (64+ characters)
- [ ] Set restrictive `CORS_ORIGINS`
- [ ] Enable `HTTPS_ONLY=true`
- [ ] Set `DEBUG=false`
- [ ] Use secure database passwords
- [ ] Rotate API keys regularly
- [ ] Enable `SECURE_COOKIES=true`
- [ ] Set appropriate `HSTS_MAX_AGE`

### 🚫 Never Do This

- ❌ Commit `.env` files to version control
- ❌ Use default/test API keys in production
- ❌ Enable debug mode in production
- ❌ Use localhost URLs in production config
- ❌ Share production credentials

### ✅ Recommended Practices

- ✅ Use environment variables in production
- ✅ Validate configurations before deployment
- ✅ Use different API keys per environment
- ✅ Enable monitoring in production
- ✅ Regularly rotate secrets
- ✅ Use least-privilege database users

## Deployment-Specific Configurations

### Heroku
```bash
# Set via Heroku CLI
heroku config:set DATABASE_URL=postgresql://...
heroku config:set ANTHROPIC_API_KEY=sk-ant-...
heroku config:set ENVIRONMENT=production
```

### Docker
```bash
# Via docker-compose environment
docker-compose -f docker-compose.yml -f docker-compose.production.yml up

# Via environment file
docker run --env-file .env.production flashcard-app
```

### VPS/Server
```bash
# Export environment variables
export DATABASE_URL=postgresql://...
export ANTHROPIC_API_KEY=sk-ant-...

# Or use systemd environment file
sudo systemctl edit flashcard-app --full
Environment=DATABASE_URL=postgresql://...
```

## Troubleshooting

### Common Issues

**Environment file not found:**
```bash
python scripts/setup-env.py list
python scripts/setup-env.py use development
```

**Database connection failed:**
```bash
# Check DATABASE_URL format
echo $DATABASE_URL

# Test connection
uv run python -c "from backend.database import Database; db = Database(); print('✅ Connected' if db.test_connection() else '❌ Failed')"
```

**API keys not working:**
```bash
# Validate environment
python scripts/setup-env.py validate

# Test API connection
curl -X POST http://localhost:8000/api/config/test
```

**Permission denied:**
```bash
# Make setup script executable
chmod +x scripts/setup-env.py
```

### Debug Commands

```bash
# Check current environment
python -c "import os; print(f'Environment: {os.getenv(\"ENVIRONMENT\", \"not set\")}')"

# Validate database
python -c "from backend.database import Database; db = Database(); print(db.get_db_info())"

# Test AI providers
curl -X POST http://localhost:8000/api/config/test -H "Content-Type: application/json" -d '{"provider": "anthropic"}'
```
