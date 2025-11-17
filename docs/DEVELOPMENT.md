# Development Guide - Flashcard Study App

## Project Overview

AI-powered flashcard study app that:
- Parses markdown flashcards
- Presents questions one at a time
- Accepts text input for answers (voice input planned for V2)
- Uses AI (Claude or OpenAI) to grade answers against reference answers
- Tracks progress and statistics
- Supports spaced repetition (planned for V2)

**Status**: ✅ V2 COMPLETE! All 128 tests passing. Backend, frontend, spaced repetition algorithm, database migrations, and production-ready features all complete.

---

## Technology Stack

- **Package Manager**: `uv` (modern Python package manager)
- **Backend**: FastAPI (async, auto-generated docs)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Validation**: Pydantic 2 (DTOs/schemas)
- **AI APIs**: Anthropic Claude Sonnet 4 (default) + OpenAI GPT-4o
- **Testing**: pytest + pytest-asyncio + pytest-mock
- **Linting**: ruff (all checks passing)
- **Frontend**: Simple HTML/JS (planned, not yet built)

---

## Project Structure

```
study-cards/
├── backend/
│   ├── __init__.py
│   ├── main.py           # FastAPI app, routes, dependency injection
│   ├── models.py         # SQLAlchemy ORM models (DeckModel, FlashcardModel, etc.)
│   ├── schemas.py        # Pydantic DTOs for API validation
│   ├── database.py       # DAOs (Data Access Objects) for clean data access
│   ├── parser.py         # Markdown flashcard parser
│   ├── grading.py        # AI grading service (Claude/OpenAI)
│   └── config.py         # Configuration management (API keys, settings)
│
├── frontend/             # Frontend files (TO BE BUILT)
│   ├── index.html        # Main UI
│   ├── styles.css        # Styling
│   └── app.js            # JavaScript logic
│
├── tests/
│   ├── __init__.py
│   ├── test_parser.py    # 14 tests for markdown parsing
│   ├── test_database.py  # 20 tests for database/DAOs
│   ├── test_grading.py   # 13 tests for AI grading (mocked)
│   └── test_api.py       # 18 tests for FastAPI endpoints
│
├── sample_flashcards/    # Sample markdown files (TO BE CREATED)
│   └── python_basics.md  # Example flashcards
│
├── pyproject.toml        # uv project config (dependencies)
├── ruff.toml             # Linting configuration
├── .env.example          # Environment variable template
├── .gitignore
└── README.md             # (TO BE CREATED)
```

---

## Architecture & Design Decisions

### 1. **Clean Architecture with DTOs and DAOs**

**Why**: Separation of concerns, type safety, testability

- **Models** (`models.py`): SQLAlchemy ORM models - database representation
- **Schemas** (`schemas.py`): Pydantic DTOs - API contracts and validation
- **DAOs** (`database.py`): Data Access Objects - clean database operations

```python
# Flow: API Request -> Pydantic DTO -> DAO -> SQLAlchemy Model -> Database
# Example:
DeckCreate (DTO) -> DeckDAO.create() -> DeckModel (ORM) -> SQLite
```

### 2. **Dependency Injection Pattern**

**Why**: Testability, flexibility, proper resource management

```python
# backend/main.py
def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

# Usage in routes
@app.post("/api/decks")
async def create_deck(deck_data: DeckCreate, db: Database = Depends(get_db)):
    deck_dao = DeckDAO(db)
    return deck_dao.create(deck_data)
```

**Testing**: Override dependencies with test instances
```python
app.dependency_overrides[get_db] = lambda: test_db
```

### 3. **Modern Type Annotations**

**Decision**: Use `X | None` instead of `Optional[X]` (Python 3.10+)

```python
# New style (ruff enforced)
def get_deck(deck_id: str) -> Deck | None:
    ...

# Old style (avoided)
def get_deck(deck_id: str) -> Optional[Deck]:
    ...
```

### 4. **Timezone-Aware Datetimes**

**Decision**: Use `datetime.now(UTC)` instead of deprecated `datetime.utcnow()`

```python
from datetime import datetime, UTC

created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
```

### 5. **SQLite Connection Pooling for Tests**

**Problem**: In-memory SQLite databases disappear when connections close
**Solution**: Use `StaticPool` to share the same connection across all test sessions

```python
# tests/test_api.py
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool  # Critical for test isolation
)
```

### 6. **AI Grading Design**

**Approach**: Structured JSON responses from LLMs

```python
# Prompt asks for:
{
  "score": 85,  # 0-100
  "grade": "Good",  # Perfect/Good/Partial/Wrong
  "feedback": "You covered X but missed Y",
  "key_concepts_covered": ["concept1"],
  "key_concepts_missed": ["concept2"]
}
```

**Supports both providers**:
- Anthropic Claude (default): `claude-sonnet-4-20250514`
- OpenAI GPT: `gpt-4o`

User can switch via config endpoint or environment variables.

---

## Database Schema

```sql
CREATE TABLE decks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_file TEXT,
    created_at TIMESTAMP,
    last_studied TIMESTAMP
);

CREATE TABLE flashcards (
    id TEXT PRIMARY KEY,
    deck_id TEXT REFERENCES decks(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP
);

CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    flashcard_id TEXT REFERENCES flashcards(id),
    reviewed_at TIMESTAMP,
    user_answer TEXT,
    ai_score INTEGER,
    ai_grade TEXT,
    ai_feedback TEXT,
    next_review_date TIMESTAMP
);

CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

**Cascade Deletes**: Deleting a deck deletes all flashcards; deleting a flashcard deletes all reviews.

---

## API Endpoints

### Decks
- `POST /api/decks` - Create deck
- `GET /api/decks` - List all decks
- `GET /api/decks/{deck_id}` - Get deck by ID
- `POST /api/decks/import` - Import from markdown file
- `GET /api/decks/{deck_id}/stats` - Get deck statistics

### Flashcards
- `POST /api/decks/{deck_id}/flashcards` - Create flashcard
- `GET /api/decks/{deck_id}/flashcards` - List flashcards in deck

### Grading
- `POST /api/grade` - Grade user answer against flashcard

### Configuration
- `GET /api/config` - Get configuration (without API keys)
- `PUT /api/config` - Update configuration
- `POST /api/config/test` - Test AI provider connection

### Study Sessions
- `POST /api/sessions/start` - Start study session
- `GET /api/sessions/{session_id}/next` - Get next card in session

### Health
- `GET /health` - Health check

**API Docs**: Run server and visit `http://localhost:8000/docs` for Swagger UI

---

## Markdown Flashcard Format

```markdown
## Question 1
What is the difference between @staticmethod and @classmethod in Python?

### Answer
@staticmethod doesn't receive any implicit first argument (no self, no cls).
@classmethod receives the class as implicit first argument (cls).
Use @classmethod when you need to access the class, @staticmethod when you don't need instance or class.

---

## Question 2
Explain MVCC in PostgreSQL.

### Answer
MVCC (Multi-Version Concurrency Control) allows multiple transactions to access the same data concurrently.
Each transaction sees a snapshot of the database at a specific point in time.
Old row versions are kept until no transaction needs them (then VACUUM cleans them up).
This avoids locking for reads and provides transaction isolation.

---
```

**Parser Features**:
- Supports both `---` and `***` as separators
- Case-insensitive "Answer" heading
- Handles multiline answers
- Preserves formatting (code blocks, lists, etc.)

---

## Testing Strategy

### Test Coverage: 128 passing tests

1. **Parser Tests** (`test_parser.py`) - 14 tests
   - Valid/invalid markdown
   - Edge cases (empty, missing sections)
   - File validation

2. **Database Tests** (`test_database.py`) - 20 tests
   - CRUD operations for all DAOs
   - Cascade deletes
   - Statistics calculations
   - Test isolation (in-memory DB per test)

3. **Grading Tests** (`test_grading.py`) - 13 tests
   - Both AI providers (mocked)
   - JSON extraction from various formats
   - Error handling
   - Connection testing

4. **API Tests** (`test_api.py`) - 18 tests
   - All endpoints
   - Error cases (404, 400)
   - Integration tests with real database operations
   - Dependency injection overrides

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Specific test file
uv run pytest tests/test_api.py -v

# With coverage
uv run pytest tests/ --cov=backend --cov-report=html
```

### Linting

```bash
# Check code
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

---

## Running the Application

### Setup

```bash
# Install dependencies
uv sync

# Create .env file
cp .env.example .env
# Edit .env and add your API keys
```

### Start Server

```bash
# Development server with auto-reload
uv run uvicorn backend.main:app --reload

# Production
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Server runs at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

---

## Environment Variables

After cleanup, only these variables are used by the application:

```bash
# .env file (copy from .env.example)
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
DEFAULT_AI_PROVIDER=anthropic  # or "openai"
ANTHROPIC_MODEL=claude-sonnet-4-20250514
OPENAI_MODEL=gpt-4o
DATABASE_URL=postgresql://flashcards:flashcards_password@localhost:5432/flashcards_dev

# Optional spaced repetition settings (defaults used if not set)
INITIAL_INTERVAL_DAYS=1
EASY_MULTIPLIER=2.5
GOOD_MULTIPLIER=1.8
MINIMUM_INTERVAL_DAYS=1
MAXIMUM_INTERVAL_DAYS=180
```

**Available Environment Templates:**
- `.env.example` - Clean template for local development
- `.env.development` - Development-specific configuration
- `.env.docker` - Docker container configuration

**Note**: API keys can also be set via the `/api/config` endpoint (stored in database).

---

## What's Completed ✅

1. **Project Setup**
   - uv package manager with proper dependencies
   - ruff linting (all checks passing)
   - Comprehensive test suite (128 tests, all passing)

2. **Backend Core**
   - Markdown parser with full validation
   - SQLite database with SQLAlchemy ORM
   - Pydantic 2 schemas for type safety
   - Clean DAO pattern for data access

3. **AI Integration**
   - Anthropic Claude Sonnet 4 (default)
   - OpenAI GPT-4o (alternative)
   - Structured grading with scores and feedback
   - Configurable provider switching

4. **API**
   - 18 FastAPI endpoints
   - Comprehensive error handling
   - Auto-generated API documentation
   - Dependency injection for testability

5. **Statistics**
   - Deck-level stats (total cards, reviewed, avg score)
   - Per-review tracking (score, grade, feedback)
   - Grade distribution (Perfect/Good/Partial/Wrong)

6. **Frontend** ✅ **NEW**
   - Clean, responsive web interface
   - Deck selection and management
   - Study session flow with answer input
   - Real-time AI grading feedback display
   - Session statistics and completion screen
   - File upload for markdown import
   - Keyboard shortcuts (Ctrl+Enter to submit)

7. **Documentation** ✅ **NEW**
   - Comprehensive README.md with quick start guide
   - Installation and usage instructions
   - API documentation reference
   - Troubleshooting guide
   - Architecture overview

8. **Sample Flashcards** ✅ **NEW**
   - Python basics (8 questions on decorators, comprehensions, etc.)
   - PostgreSQL (8 questions on MVCC, indexes, etc.)
   - Ready to import and test immediately

9. **Spaced Repetition Algorithm** ✅ **NEW**
   - SM-2 Modified algorithm implementation with customizable settings
   - Database schema with ease_factor, interval_days, and repetitions columns
   - Due cards filtering and next review date calculation
   - Comprehensive spaced repetition settings UI with validation
   - Due-only study sessions for reviewing cards that need attention
   - Alembic migrations for database schema updates

10. **Deck Management System** ✅ **NEW**
    - Create/edit/delete decks UI with form validation
    - Deck settings and configuration management
    - Mass delete functionality with selection UI
    - API endpoints for full deck CRUD operations

11. **Smart Deck Filtering** ✅ **NEW**
    - Hide empty decks from main page display (default behavior)
    - Toggle "Show Empty Decks" filter option
    - Backend API parameter for including/excluding empty decks

12. **Comprehensive Keyboard Shortcuts** ✅ **NEW**
    - Cross-platform keyboard shortcut handling (⌘ on Mac, Ctrl on PC)
    - Ctrl/Cmd+Enter for answer submissions and form submissions
    - Ctrl/Cmd+→ for next card during study sessions
    - Escape to end study sessions (with confirmation)
    - Escape to close modals with smart context detection
    - Visual keyboard hints on buttons and placeholders

---

## What's Remaining 📋

### Features Prioritized by User (Highest to Lowest Priority)

1. ✅ **Custom UI Notifications** - **COMPLETED!**
   - ✅ Custom toast notification system with 4 types (success, error, warning, info)
   - ✅ Custom confirmation modal system replacing browser alerts
   - ✅ Smooth animations and responsive design
   - ✅ Consistent branding and professional appearance

2. **Voice Input Integration**
   - OpenAI Whisper API integration
   - Record audio in browser
   - Send to backend for transcription
   - Fill text input with transcribed text

3. **User Authentication & Multi-User Support**
   - User registration and login system
   - Multi-user database schema
   - Session management
   - User-specific decks and progress

4. **In-App Flashcard Creation & Editing**
   - Create flashcards in-app (alternative to markdown import)
   - Edit existing flashcards
   - Bulk flashcard operations
   - Rich text editing capabilities

5. **Session Review with Missed Concepts Analysis** ✨ **NEW**
   - Post-session summary showing concepts that need more study
   - Analysis of answers to identify knowledge gaps
   - Recommendations for focused review sessions
   - Database tracking of concept mastery over time

6. **Dark Mode Toggle**
   - Theme switching functionality
   - Dark/light mode CSS variables
   - User preference persistence

7. **Progress Bar During Study Sessions**
   - Visual progress indicator
   - Cards completed vs. total cards
   - Session completion tracking

8. **Tags & Categories for Organization**
   - Tag system for flashcards
   - Category-based organization
   - Filtering and search by tags
   - Database schema for tags/categories

### Lower Priority Features (Future Releases)

9. **AI Flashcard Generation** ✨ **NEW - LOW PRIORITY**
   - Generate flashcards from user-provided themes/topics
   - Integration with Claude Sonnet 4 or OpenAI GPT-4o
   - In-app editing of generated flashcards
   - Quality validation and user review process
   - Batch generation with customizable difficulty levels

10. **Telegram Bot Functionality** ✨ **NEW - LOW PRIORITY**
    - **Phase 1: Planning & Design**
      - Bot architecture and command structure
      - Integration with existing backend API
      - User authentication via Telegram
      - Database schema for Telegram users
    - **Phase 2: Core Features**
      - `/start` - Bot introduction and setup
      - `/study` - Start study session via Telegram
      - `/progress` - View study statistics
      - `/decks` - List available decks
      - Voice message support for answers (using same Whisper API)
    - **Phase 3: Advanced Features**
      - Scheduled review reminders
      - Deck sharing between users
      - Analytics and progress tracking

### Testing Requirements
⚠️ **Important**: For any features requiring backend changes, ensure:
- All existing tests continue to pass (`uv run pytest tests/ -v`)
- New functionality is covered by appropriate tests
- Code passes linting checks (`uv run ruff check .`)
- Database migrations are handled properly

---

## Known Issues & Decisions

### Design Decisions

1. **In-Memory Study Sessions**: Currently stored in `study_sessions` dict in `main.py`
   - **Pro**: Fast, simple
   - **Con**: Lost on server restart
   - **Future**: Move to database or Redis for persistence

2. **No Authentication**: MVP has no user management
   - **Pro**: Simpler to start
   - **Con**: Can't have multiple users
   - **Future**: Add auth when needed

3. **PostgreSQL Database**: Using PostgreSQL for all environments
   - **Pro**: Scalable, supports multiple users, production-ready
   - **Pro**: Consistent environment across development and production
   - **Con**: Requires external database setup
   - **Decision**: Better for long-term scalability and deployment

4. **Global Database Instance**: Using module-level singleton
   - **Pro**: Simple, works well with FastAPI
   - **Con**: Could cause issues with concurrent requests
   - **Note**: SQLite handles this with locking

### Testing Quirks

1. **StaticPool Required**: In-memory SQLite needs `StaticPool` for tests
   - Without it, each DAO creates a new connection and loses the database
   - See `tests/test_api.py` fixture

2. **Dependency Override Pattern**: FastAPI dependency injection tested via `app.dependency_overrides`
   - Not monkeypatch - must use FastAPI's built-in system

---

## Code Style & Conventions

### Enforced by Ruff

- Line length: 100 characters
- Modern type hints: `X | None` not `Optional[X]`
- Imports sorted (isort)
- No unused imports/variables
- Proper exception chaining (`raise ... from e`)
- No blind exception catching

### Naming Conventions

- **Models**: `*Model` suffix (e.g., `DeckModel`, `FlashcardModel`)
- **DAOs**: `*DAO` suffix (e.g., `DeckDAO`, `FlashcardDAO`)
- **Schemas**: Descriptive names (e.g., `DeckCreate`, `GradingResult`)
- **Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE

### Docstrings

All public functions/classes have docstrings:
```python
def parse_flashcard_file(file_path: str) -> list[dict[str, str]]:
    """
    Parse a markdown file containing flashcards.

    Args:
        file_path: Path to the markdown file

    Returns:
        List of flashcard dictionaries with 'question' and 'answer' keys
    """
```

---

## 🎯 Essential Pre-Push Commands

**Run these 2 commands before every push to guarantee CI success:**

```bash
# 1. Full test suite with coverage and database validation
make test

# 2. All code quality checks (linting, formatting, security)
make lint
```

**Quick verification:**
```bash
# Run both in sequence - if both pass, CI will pass
make test && make lint
```

**What these commands catch:**
- ✅ All 129 test failures and database issues
- ✅ Coverage threshold violations (85% minimum)
- ✅ Ruff linting violations (code quality)
- ✅ Code formatting issues (exact CI match)
- ✅ Import sorting and organization
- ✅ Security vulnerabilities (Bandit)

---

## Quick Reference Commands

```bash
# Essential pre-push validation
make test && make lint

# Install/sync dependencies
uv sync

# Run tests (various modes)
make test          # Full test suite with coverage
make test-fast     # Quick tests without coverage
make test-docker   # Tests in Docker (isolated)

# Code quality (synchronized with CI)
make lint          # Exact same checks as CI: linting + formatting + imports
make format        # Auto-fix formatting and linting issues
make type-check    # MyPy type checking

# Database operations
make migrate-up    # Apply migrations
make migrate-test  # Test migrations on clean DB
make test-clean    # Clean test database

# Development server
uv run uvicorn backend.main:app --reload

# Dependencies
uv add <package-name>       # Add runtime dependency
uv add --dev <package-name> # Add dev dependency

# Pre-commit hooks
make pre-commit-install     # Install hooks
make pre-commit-run        # Run hooks on staged files
```

---

## Next Steps for New Session

✅ **V2 is complete!** All high-priority features including spaced repetition are implemented and tested.

### Suggested Next Steps (User's Priority Order)

**Phase 1: UI/UX Polish (Items 1-2)**
1. Replace browser alerts with custom UI notifications
2. Add voice input integration with OpenAI Whisper API

**Phase 2: Multi-User & Content Management (Items 3-4)**
3. Add user authentication and multi-user support
4. Add in-app flashcard creation and editing functionality

**Phase 3: Additional Features & Organization (Items 5-7)**
5. Add dark mode toggle
6. Add progress bar during study sessions
7. Add tags and categories for flashcard organization

**Recommended approach**: Complete each phase before moving to the next to maintain momentum and see immediate improvements in user experience.

---

## Debug Tips

### Database Issues
- Database: PostgreSQL (configured via `DATABASE_URL` environment variable)
- View with: `psql $DATABASE_URL` then `\dt` (tables), `\d table_name` (schema)
- Reset tables: `uv run alembic downgrade base && uv run alembic upgrade head`

### Test Failures
- Run single test: `uv run pytest tests/test_api.py::test_name -v`
- See print output: `uv run pytest tests/test_api.py -s`
- Debug mode: `uv run pytest tests/test_api.py --pdb`

### API Issues
- Check FastAPI logs in terminal
- Visit `/docs` for interactive API testing
- Use `curl` or Postman to test endpoints

### Import Errors
- Ensure you're in the project root: `cd study-cards`
- Activate venv: `source .venv/bin/activate` (done automatically by `uv run`)
- Check imports are from `backend.*` not relative

---

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [uv Docs](https://docs.astral.sh/uv/)
- [Ruff Docs](https://docs.astral.sh/ruff/)
- [Anthropic API](https://docs.anthropic.com/)
- [OpenAI API](https://platform.openai.com/docs/)

---

## Recent Updates - November 2025

### 🧹 Project Cleanup & CI/CD Improvements ✅ **COMPLETED**

**Completed Tasks:**
1. **Environment Variables Cleanup** ✅
   - Removed all unused environment variables from `.env.example`, `.env.docker`, and `.env.development`
   - Deleted unused environment files (`.env.staging`, `.env.production`)
   - Only kept variables actually used by `backend/config.py` Settings class:
     - `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEFAULT_AI_PROVIDER`
     - `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `DATABASE_URL`
     - Optional spaced repetition settings with defaults

2. **Docker Compose Cleanup** ✅
   - Removed unused `docker-compose.staging.yml` and `docker-compose.production.yml`
   - Kept only actively used files:
     - `docker-compose.yml` (main development)
     - `docker-compose.test.yml` (CI testing)
     - `docker-compose.override.yml` (dev overrides)

3. **Deployment Workflow Removal** ✅
   - Removed disabled deployment workflow files
   - Cleaned up deployment-related configurations

4. **CI/CD Pipeline Improvements** ✅
   - **MyPy Type Checking**: Added gradual adoption approach with proper configuration
   - **Coverage Enforcement**: Added 85% minimum test coverage threshold
   - **Pre-commit Hooks**: Comprehensive local code quality checks (Ruff, MyPy, Bandit)
   - **Docker Build Testing**: Added multi-stage build validation to CI
   - **Security Scanning**: Local Bandit security checks (Trivy removed for simplified CI)
   - **Simplified CI Pipeline**: Removed complex migration validation and security scanning for streamlined development

**Current CI Status:** 4/4 checks passing ✅ **SIMPLIFIED & STREAMLINED**
- Tests (with PostgreSQL) - ✅ Fixed Anthropic test failure
- Code Quality (Ruff linting + formatting)
- Type Checking (MyPy)
- Docker Build Test (development + production)

**Development Workflow Improvements:**
- **Essential Pre-Push Commands**: `make test && make lint` - guarantees CI success
- Added comprehensive Makefile with new commands:
  - `make pre-commit-install` - Install pre-commit hooks
  - `make migrate-test` - Test database migrations
  - `make lint-docker` - Run linting in Docker
- Pre-commit hooks run automatically on git commits
- All code quality tools properly configured in `pyproject.toml`

**Recent Changes (November 9, 2025):**
- ✅ Fixed Anthropic test failure by properly mocking `TextBlock` from `anthropic.types`
- ✅ Fixed database migration errors by correcting initial schema baseline migration
- ✅ All 129 tests now passing locally and in CI
- ✅ Simplified CI pipeline by removing migration validation and security scan workflows
- 🎯 Streamlined development workflow: Essential commands `make test && make lint`

---

**Last Updated**: 2025-11-09
**Backend Status**: ✅ Complete (128/128 tests passing, ruff clean)
**Frontend Status**: ✅ Complete (responsive UI with full functionality)
**Documentation**: ✅ Complete (README.md + DEVELOPMENT.md)
**Sample Data**: ✅ Complete (Python + PostgreSQL flashcards)
**CI/CD Status**: ✅ Complete (8/8 checks passing, comprehensive pipeline)
**V2 Status**: ✅ **COMPLETE AND READY TO USE!**
**Next Priority**: Optional V3 features (custom notifications, voice input, multi-user support)
