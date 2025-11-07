"""
Tests for FastAPI endpoints (integration tests).
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import main
from backend.config import ConfigManager
from backend.database import ConfigDAO, Database, DeckDAO, FlashcardDAO, ReviewDAO
from backend.grading import GradingService
from backend.main import app, get_config_manager, get_db, get_grading_service
from backend.models import Base
from backend.schemas import GradingResult


# Test fixtures
@pytest.fixture
def test_db():
    """Create a fresh in-memory test database for each test."""
    # Use StaticPool to ensure all sessions share the same in-memory database connection
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool  # Critical for in-memory SQLite testing
    )

    # Create tables
    Base.metadata.create_all(engine)

    # Create a custom Database instance
    db = Database.__new__(Database)
    db.engine = engine
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield db

    # Clean up
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(test_db):
    """Create a test client with dependency overrides."""
    # Create service instances that use test_db
    config_dao = ConfigDAO(test_db)
    config_manager = ConfigManager(config_dao=config_dao)
    grading_service = GradingService(
        anthropic_api_key="test_key",
        openai_api_key="test_key",
        default_provider="anthropic"
    )

    # Use FastAPI's dependency override system
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_grading_service] = lambda: grading_service
    app.dependency_overrides[get_config_manager] = lambda: config_manager

    # Ensure each test starts fresh by clearing the study sessions
    main.study_sessions.clear()

    with TestClient(app) as test_client:
        yield test_client

    # Clean up after test
    app.dependency_overrides.clear()


@pytest.fixture
def sample_flashcard_file(tmp_path):
    """Create a sample flashcard markdown file."""
    file_path = tmp_path / "sample.md"
    content = """
## What is Python?

### Answer
Python is a high-level programming language known for its readability and versatility.

---

## What is JavaScript?

### Answer
JavaScript is a scripting language primarily used for web development.

---
"""
    file_path.write_text(content)
    return str(file_path)


# Health check test
def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# Deck endpoints
def test_create_deck(client):
    """Test creating a deck."""
    response = client.post(
        "/api/decks",
        json={"name": "Python Basics", "source_file": "/path/to/file.md"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Python Basics"
    assert data["source_file"] == "/path/to/file.md"
    assert "id" in data


def test_get_all_decks(client):
    """Test getting all decks including empty ones."""
    # Create some decks first
    client.post("/api/decks", json={"name": "Deck 1"})
    client.post("/api/decks", json={"name": "Deck 2"})

    # Include empty decks to test the original behavior
    response = client.get("/api/decks?include_empty=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {d["name"] for d in data} == {"Deck 1", "Deck 2"}


def test_get_decks_filter_empty_by_default(client):
    """Test that empty decks are filtered out by default."""
    # Create decks - one with flashcards, one empty
    deck1_response = client.post("/api/decks", json={"name": "Deck with cards"})
    client.post("/api/decks", json={"name": "Empty deck"})

    deck1_id = deck1_response.json()["id"]

    # Add flashcard to first deck
    client.post(
        f"/api/decks/{deck1_id}/flashcards",
        json={"question": "Test question?", "answer": "Test answer"}
    )

    # By default, should only return non-empty decks
    response = client.get("/api/decks")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deck with cards"
    assert data[0]["stats"]["total_cards"] == 1


def test_get_decks_include_empty(client):
    """Test getting all decks including empty ones."""
    # Create decks - one with flashcards, one empty
    deck1_response = client.post("/api/decks", json={"name": "Deck with cards"})
    client.post("/api/decks", json={"name": "Empty deck"})

    deck1_id = deck1_response.json()["id"]

    # Add flashcard to first deck
    client.post(
        f"/api/decks/{deck1_id}/flashcards",
        json={"question": "Test question?", "answer": "Test answer"}
    )

    # With include_empty=true, should return all decks
    response = client.get("/api/decks?include_empty=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    deck_names = {d["name"] for d in data}
    assert deck_names == {"Deck with cards", "Empty deck"}

    # Check card counts
    for deck in data:
        if deck["name"] == "Deck with cards":
            assert deck["stats"]["total_cards"] == 1
        else:  # Empty deck
            assert deck["stats"]["total_cards"] == 0


def test_get_deck_by_id(client):
    """Test getting a specific deck."""
    # Create a deck
    create_response = client.post("/api/decks", json={"name": "Test Deck"})
    deck_id = create_response.json()["id"]

    # Get the deck
    response = client.get(f"/api/decks/{deck_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == deck_id
    assert data["name"] == "Test Deck"


def test_get_deck_not_found(client):
    """Test getting a non-existent deck."""
    response = client.get("/api/decks/nonexistent-id")
    assert response.status_code == 404


def test_update_deck(client):
    """Test updating a deck."""
    # Create a deck
    create_response = client.post("/api/decks", json={"name": "Original Name", "source_file": "original.md"})
    deck_id = create_response.json()["id"]

    # Update the deck
    response = client.put(
        f"/api/decks/{deck_id}",
        json={"name": "Updated Name", "source_file": "updated.md"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == deck_id
    assert data["name"] == "Updated Name"
    assert data["source_file"] == "updated.md"


def test_update_deck_partial(client):
    """Test updating only some fields of a deck."""
    # Create a deck
    create_response = client.post("/api/decks", json={"name": "Original Name", "source_file": "original.md"})
    deck_id = create_response.json()["id"]

    # Update only the name
    response = client.put(
        f"/api/decks/{deck_id}",
        json={"name": "New Name Only"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == deck_id
    assert data["name"] == "New Name Only"
    assert data["source_file"] == "original.md"  # Should remain unchanged


def test_update_deck_not_found(client):
    """Test updating a non-existent deck."""
    response = client.put(
        "/api/decks/nonexistent-id",
        json={"name": "New Name"}
    )
    assert response.status_code == 404


def test_delete_deck(client):
    """Test deleting a deck."""
    # Create a deck with flashcards
    create_response = client.post("/api/decks", json={"name": "Test Deck"})
    deck_id = create_response.json()["id"]

    # Add a flashcard to the deck
    client.post(
        f"/api/decks/{deck_id}/flashcards",
        json={"question": "Test question?", "answer": "Test answer"}
    )

    # Delete the deck
    response = client.delete(f"/api/decks/{deck_id}")

    assert response.status_code == 200
    assert "message" in response.json()

    # Verify deck is gone
    get_response = client.get(f"/api/decks/{deck_id}")
    assert get_response.status_code == 404

    # Verify flashcards are also gone (cascade delete)
    flashcards_response = client.get(f"/api/decks/{deck_id}/flashcards")
    assert flashcards_response.status_code == 404


def test_delete_deck_not_found(client):
    """Test deleting a non-existent deck."""
    response = client.delete("/api/decks/nonexistent-id")
    assert response.status_code == 404


def test_bulk_delete_decks(client):
    """Test bulk deleting multiple decks."""
    # Create some decks
    deck1 = client.post("/api/decks", json={"name": "Deck 1"}).json()
    deck2 = client.post("/api/decks", json={"name": "Deck 2"}).json()
    deck3 = client.post("/api/decks", json={"name": "Deck 3"}).json()

    # Add flashcards to one of them
    client.post(
        f"/api/decks/{deck1['id']}/flashcards",
        json={"question": "Test question?", "answer": "Test answer"}
    )

    # Bulk delete two decks
    response = client.post(
        "/api/decks/bulk-delete",
        json={"deck_ids": [deck1["id"], deck2["id"]]}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["deleted_count"] == 2
    assert data["requested_count"] == 2
    assert "Successfully deleted 2 deck(s)" in data["message"]

    # Verify decks are gone
    assert client.get(f"/api/decks/{deck1['id']}").status_code == 404
    assert client.get(f"/api/decks/{deck2['id']}").status_code == 404

    # Verify the third deck still exists
    assert client.get(f"/api/decks/{deck3['id']}").status_code == 200


def test_bulk_delete_partial_not_found(client):
    """Test bulk deleting when some decks don't exist."""
    # Create one deck
    deck1 = client.post("/api/decks", json={"name": "Deck 1"}).json()

    # Try to delete one existing and one non-existing deck
    response = client.post(
        "/api/decks/bulk-delete",
        json={"deck_ids": [deck1["id"], "nonexistent-id"]}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["deleted_count"] == 1
    assert data["requested_count"] == 2
    assert "1 deck(s) not found" in data["message"]


def test_bulk_delete_no_decks_found(client):
    """Test bulk deleting when no decks exist."""
    response = client.post(
        "/api/decks/bulk-delete",
        json={"deck_ids": ["nonexistent-1", "nonexistent-2"]}
    )

    assert response.status_code == 404


def test_bulk_delete_empty_list(client):
    """Test bulk deleting with empty deck list."""
    response = client.post(
        "/api/decks/bulk-delete",
        json={"deck_ids": []}
    )

    assert response.status_code == 422  # Validation error


def test_import_deck_from_file(client, sample_flashcard_file):
    """Test importing a deck from a markdown file."""
    response = client.post(
        "/api/decks/import-from-path",
        json={"file_path": sample_flashcard_file, "deck_name": "Imported Deck"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["deck"]["name"] == "Imported Deck"
    assert data["flashcards_count"] == 2


# Flashcard endpoints
def test_get_flashcards_for_deck(client):
    """Test getting flashcards for a deck."""
    # Create deck
    deck_response = client.post("/api/decks", json={"name": "Test Deck"})
    deck_id = deck_response.json()["id"]

    # Create flashcards
    client.post(
        f"/api/decks/{deck_id}/flashcards",
        json={"question": "Q1", "answer": "A1"}
    )
    client.post(
        f"/api/decks/{deck_id}/flashcards",
        json={"question": "Q2", "answer": "A2"}
    )

    # Get flashcards
    response = client.get(f"/api/decks/{deck_id}/flashcards")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_create_flashcard(client):
    """Test creating a flashcard."""
    # Create deck first
    deck_response = client.post("/api/decks", json={"name": "Test Deck"})
    deck_id = deck_response.json()["id"]

    # Create flashcard
    response = client.post(
        f"/api/decks/{deck_id}/flashcards",
        json={"question": "What is 2+2?", "answer": "4"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is 2+2?"
    assert data["answer"] == "4"
    assert data["deck_id"] == deck_id


# Grading endpoint
def test_grade_answer(client, mocker):
    """Test grading a user's answer."""
    # Create deck and flashcard
    deck_response = client.post("/api/decks", json={"name": "Test Deck"})
    deck_id = deck_response.json()["id"]

    flashcard_response = client.post(
        f"/api/decks/{deck_id}/flashcards",
        json={"question": "What is Python?", "answer": "A programming language"}
    )
    flashcard_id = flashcard_response.json()["id"]

    # Mock the grading service
    mock_result = GradingResult(
        score=85,
        grade="Good",
        feedback="Well done! You covered the main concept.",
        key_concepts_covered=["programming language"],
        key_concepts_missed=[]
    )

    mocker.patch.object(GradingService, 'grade_answer', return_value=mock_result)

    # Grade the answer
    response = client.post(
        "/api/grade",
        json={
            "flashcard_id": flashcard_id,
            "user_answer": "Python is a programming language"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 85
    assert data["grade"] == "Good"
    assert "Well done" in data["feedback"]


# Statistics endpoints
def test_get_deck_stats(client):
    """Test getting statistics for a deck."""
    # Create deck and flashcard
    deck_response = client.post("/api/decks", json={"name": "Test Deck"})
    deck_id = deck_response.json()["id"]

    response = client.get(f"/api/decks/{deck_id}/stats")

    assert response.status_code == 200
    data = response.json()
    assert "total_cards" in data
    assert "reviewed_cards" in data
    assert "average_score" in data


# Configuration endpoints
def test_get_config(client):
    """Test getting configuration."""
    response = client.get("/api/config")

    assert response.status_code == 200
    data = response.json()
    assert "default_provider" in data
    assert "has_anthropic_key" in data
    assert "has_openai_key" in data


def test_update_config(client):
    """Test updating configuration."""
    response = client.put(
        "/api/config",
        json={
            "anthropic_api_key": "new-anthropic-key",
            "default_provider": "anthropic"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["default_provider"] == "anthropic"


def test_test_ai_connection(client, mocker):
    """Test the AI connection test endpoint."""
    from backend.grading import GradingService

    mocker.patch.object(
        GradingService,
        'test_connection',
        return_value=(True, "Connection successful")
    )

    response = client.post(
        "/api/config/test",
        json={"provider": "anthropic"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "successful" in data["message"]


# Study session endpoints
def test_start_study_session(client):
    """Test starting a study session."""
    # Create deck with flashcards
    deck_response = client.post("/api/decks", json={"name": "Test Deck"})
    deck_id = deck_response.json()["id"]

    client.post(
        f"/api/decks/{deck_id}/flashcards",
        json={"question": "Q1", "answer": "A1"}
    )
    client.post(
        f"/api/decks/{deck_id}/flashcards",
        json={"question": "Q2", "answer": "A2"}
    )

    # Start session
    response = client.post(
        "/api/sessions/start",
        json={"deck_id": deck_id}
    )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["deck_id"] == deck_id
    assert data["total_cards"] > 0


def test_get_next_card(client):
    """Test getting the next card in a session."""
    # Create deck with flashcards
    deck_response = client.post("/api/decks", json={"name": "Test Deck"})
    deck_id = deck_response.json()["id"]

    client.post(
        f"/api/decks/{deck_id}/flashcards",
        json={"question": "Q1", "answer": "A1"}
    )

    # Start session
    session_response = client.post(
        "/api/sessions/start",
        json={"deck_id": deck_id}
    )
    session_id = session_response.json()["session_id"]

    # Get next card
    response = client.get(f"/api/sessions/{session_id}/next")

    assert response.status_code == 200
    data = response.json()
    assert "flashcard" in data
    assert "card_number" in data


# Error handling tests
def test_create_flashcard_invalid_deck(client):
    """Test creating a flashcard for non-existent deck."""
    response = client.post(
        "/api/decks/invalid-id/flashcards",
        json={"question": "Q", "answer": "A"}
    )
    assert response.status_code == 404


def test_grade_answer_invalid_flashcard(client):
    """Test grading with non-existent flashcard."""
    response = client.post(
        "/api/grade",
        json={
            "flashcard_id": "invalid-id",
            "user_answer": "Some answer"
        }
    )
    assert response.status_code == 404


def test_import_deck_invalid_file(client):
    """Test importing from non-existent file."""
    response = client.post(
        "/api/decks/import-from-path",
        json={"file_path": "/nonexistent/file.md"}
    )
    assert response.status_code == 400
