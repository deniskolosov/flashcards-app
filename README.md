# Flashcard Study App

An AI-powered flashcard study application that uses Claude Sonnet 4 or GPT-4o to intelligently grade your answers and provide detailed feedback.

## Features

- **Markdown-Based Flashcards**: Create flashcards using simple markdown syntax
- **AI Grading**: Get intelligent feedback from Claude or OpenAI on your answers
- **Detailed Feedback**: Receive scores, grades, and concept-level feedback
- **Progress Tracking**: Track your study progress with statistics and analytics
- **Study Sessions**: Organized study sessions with session statistics
- **Web Interface**: Clean, responsive web UI for studying
- **REST API**: Full-featured API for programmatic access
- **Dual AI Support**: Choose between Anthropic Claude or OpenAI GPT

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **AI**: Anthropic Claude Sonnet 4 / OpenAI GPT-4o
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Package Manager**: uv
- **Testing**: pytest with 65 passing tests
- **Linting**: ruff

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Anthropic API key and/or OpenAI API key

### Installation

1. **Clone the repository** (or navigate to the project directory):
```bash
cd study-cards
```

2. **Install dependencies**:
```bash
uv sync
```

3. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Your `.env` file should look like:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
DEFAULT_AI_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-20250514
OPENAI_MODEL=gpt-4o
DATABASE_URL=sqlite:///./study_cards.db
```

4. **Start the server**:
```bash
uv run uvicorn backend.main:app --reload
```

5. **Open your browser**:
Navigate to `http://localhost:8000` to access the web interface, or `http://localhost:8000/docs` for the API documentation.

## Usage

### Creating Flashcards

Flashcards are written in markdown format with the following structure:

```markdown
## What is Python?

### Answer
Python is a high-level, interpreted programming language known for its simple syntax and readability.

---

## Explain MVCC in PostgreSQL.

### Answer
MVCC (Multi-Version Concurrency Control) allows multiple transactions to access the same data concurrently without blocking each other.
Each transaction sees a snapshot of the database at a specific point in time.

---
```

**Format Rules:**
- Each flashcard starts with `## Question Text`
- Answer section starts with `### Answer`
- Flashcards are separated by `---` or `***`
- Supports multiline answers, code blocks, lists, etc.

### Importing Flashcards

#### Via Web Interface

1. Click "Import from Markdown" on the deck selection screen
2. Select your `.md` file
3. Optionally provide a deck name
4. Click "Upload"

#### Via API

```bash
curl -X POST "http://localhost:8000/api/decks/import" \
  -F "file=@sample_flashcards/python_basics.md" \
  -F "deck_name=Python Basics"
```

### Studying

1. Select a deck from the main screen
2. Read the question carefully
3. Type your answer in the text box
4. Click "Submit Answer" (or press Ctrl+Enter)
5. Review the AI feedback, score, and concepts
6. Click "Next Card" to continue

### Sample Flashcards

The project includes two sample flashcard sets:

- `sample_flashcards/python_basics.md` - 8 Python concept questions
- `sample_flashcards/postgresql.md` - 8 PostgreSQL concept questions

Import these to get started quickly!

## API Endpoints

### Decks

- `POST /api/decks` - Create a new deck
- `GET /api/decks` - List all decks with statistics
- `GET /api/decks/{deck_id}` - Get a specific deck
- `POST /api/decks/import` - Import deck from uploaded markdown file
- `POST /api/decks/import-from-path` - Import deck from local file path
- `GET /api/decks/{deck_id}/stats` - Get deck statistics

### Flashcards

- `GET /api/decks/{deck_id}/flashcards` - List all flashcards in a deck
- `POST /api/decks/{deck_id}/flashcards` - Create a flashcard

### Grading

- `POST /api/grade` - Grade a user's answer
  ```json
  {
    "flashcard_id": "card-uuid",
    "user_answer": "Your answer here"
  }
  ```

### Study Sessions

- `POST /api/sessions/start` - Start a study session
  ```json
  {
    "deck_id": "deck-uuid",
    "card_limit": 10  // optional
  }
  ```
- `GET /api/sessions/{session_id}/next` - Get next card in session

### Configuration

- `GET /api/config` - Get current configuration (without API keys)
- `PUT /api/config` - Update configuration
- `POST /api/config/test` - Test AI provider connection

### Interactive API Docs

Visit `http://localhost:8000/docs` for full interactive API documentation powered by Swagger UI.

## Development

### Project Structure

```
study-cards/
├── backend/
│   ├── main.py           # FastAPI app with routes
│   ├── models.py         # SQLAlchemy ORM models
│   ├── schemas.py        # Pydantic DTOs
│   ├── database.py       # Data Access Objects (DAOs)
│   ├── parser.py         # Markdown parser
│   ├── grading.py        # AI grading service
│   └── config.py         # Configuration management
├── frontend/
│   ├── index.html        # Main UI
│   ├── styles.css        # Styling
│   └── app.js            # JavaScript application logic
├── tests/                # 65 passing tests
├── sample_flashcards/    # Example markdown files
├── pyproject.toml        # Dependencies (managed by uv)
├── ruff.toml             # Linting configuration
└── DEVELOPMENT.md        # Comprehensive dev guide
```

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

### Adding Dependencies

```bash
# Add runtime dependency
uv add package-name

# Add dev dependency
uv add --dev package-name
```

## Architecture

### Backend Architecture

The backend follows a clean architecture pattern with clear separation of concerns:

- **Models** (`models.py`): SQLAlchemy ORM models for database tables
- **Schemas** (`schemas.py`): Pydantic DTOs for API validation and type safety
- **DAOs** (`database.py`): Data Access Objects for database operations
- **Services** (`grading.py`, `parser.py`): Business logic and external integrations
- **Routes** (`main.py`): FastAPI endpoints and dependency injection

### AI Grading

The AI grading system sends your answer along with the question and reference answer to either Claude or OpenAI. The AI responds with:

- **Score**: 0-100 numerical score
- **Grade**: Perfect / Good / Partial / Wrong
- **Feedback**: Detailed explanation of what you got right and wrong
- **Concepts Covered**: List of key concepts you mentioned
- **Concepts Missed**: List of key concepts you didn't cover

This structured feedback helps you understand not just whether your answer was correct, but specifically what you need to focus on.

### Database Schema

```sql
decks
  ├── id (PRIMARY KEY)
  ├── name
  ├── source_file
  ├── created_at
  └── last_studied

flashcards
  ├── id (PRIMARY KEY)
  ├── deck_id (FOREIGN KEY -> decks)
  ├── question
  ├── answer
  └── created_at

reviews
  ├── id (PRIMARY KEY)
  ├── flashcard_id (FOREIGN KEY -> flashcards)
  ├── reviewed_at
  ├── user_answer
  ├── ai_score
  ├── ai_grade
  ├── ai_feedback
  └── next_review_date

config
  ├── key (PRIMARY KEY)
  └── value
```

## Configuration

### Environment Variables

All configuration can be set via environment variables in `.env`:

- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `OPENAI_API_KEY` - Your OpenAI API key
- `DEFAULT_AI_PROVIDER` - Default provider: "anthropic" or "openai"
- `ANTHROPIC_MODEL` - Claude model (default: claude-sonnet-4-20250514)
- `OPENAI_MODEL` - OpenAI model (default: gpt-4o)
- `DATABASE_URL` - Database connection string (default: sqlite:///./study_cards.db)

### Runtime Configuration

Configuration can also be updated at runtime via the API:

```bash
curl -X PUT "http://localhost:8000/api/config" \
  -H "Content-Type: application/json" \
  -d '{
    "default_ai_provider": "openai",
    "anthropic_api_key": "sk-ant-...",
    "openai_api_key": "sk-..."
  }'
```

## Troubleshooting

### Database Issues

- Database file location: `./study_cards.db`
- To reset database: `rm study_cards.db` (tables will be recreated on next run)
- To inspect database: `sqlite3 study_cards.db` then use `.tables`, `.schema`, etc.

### Import Errors

- Ensure you're running from the project root: `cd study-cards`
- Use `uv run` to ensure correct environment
- Check that imports use `backend.*` format (not relative imports)

### API Connection Issues

- Verify API keys are set correctly in `.env` or via configuration endpoint
- Test connection: `POST /api/config/test` with `{"provider": "anthropic"}` or `{"provider": "openai"}`
- Check server logs for detailed error messages

### Frontend Not Loading

- Ensure server is running: `uv run uvicorn backend.main:app --reload`
- Check that `frontend/` directory exists and contains `index.html`, `styles.css`, `app.js`
- Verify you're accessing `http://localhost:8000` (not port 8080)

## Future Features (V2)

- **Voice Input**: Use OpenAI Whisper API for speech-to-text
- **Spaced Repetition**: Implement SM-2 or similar algorithm for optimal review scheduling
- **Dark Mode**: Theme toggle for better studying at night
- **Keyboard Shortcuts**: Faster navigation and submission
- **Enhanced Statistics**: More detailed analytics and progress visualization
- **Multiple Users**: User authentication and personal decks
- **Deck Sharing**: Export/import deck bundles
- **Mobile App**: Native mobile application

## Testing

The project includes comprehensive test coverage:

- **65 total tests** across 4 test files
- **100% passing** - all tests green
- **Test-driven development** approach
- Tests cover: parsers, database operations, AI grading (mocked), and API endpoints

Run tests with: `uv run pytest tests/ -v`

## License

This project is provided as-is for educational and personal use.

## Contributing

For development guidelines, architecture decisions, and detailed documentation, see [DEVELOPMENT.md](DEVELOPMENT.md).

## Support

- **Issues**: Report bugs or request features via GitHub issues
- **API Documentation**: Full interactive docs at `http://localhost:8000/docs`
- **Development Guide**: See `DEVELOPMENT.md` for comprehensive developer documentation

---

**Built with FastAPI, Claude AI, and modern Python tooling.**
