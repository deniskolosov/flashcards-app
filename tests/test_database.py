"""
Tests for database models and DAOs.
"""
from datetime import datetime

import pytest

from backend.database import ConfigDAO, Database, DeckDAO, FlashcardDAO, ReviewDAO
from backend.schemas import DeckCreate, FlashcardCreate, ReviewCreate


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    database = Database("sqlite:///:memory:")
    yield database


@pytest.fixture
def deck_dao(db):
    """Create a DeckDAO for testing."""
    return DeckDAO(db)


@pytest.fixture
def flashcard_dao(db):
    """Create a FlashcardDAO for testing."""
    return FlashcardDAO(db)


@pytest.fixture
def review_dao(db):
    """Create a ReviewDAO for testing."""
    return ReviewDAO(db)


@pytest.fixture
def config_dao(db):
    """Create a ConfigDAO for testing."""
    return ConfigDAO(db)


# Deck DAO Tests
def test_create_deck(deck_dao):
    """Test creating a deck."""
    deck_data = DeckCreate(name="Python Basics", source_file="/path/to/file.md")
    deck = deck_dao.create(deck_data)

    assert deck.id is not None
    assert deck.name == "Python Basics"
    assert deck.source_file == "/path/to/file.md"
    assert deck.created_at is not None


def test_get_deck_by_id(deck_dao):
    """Test retrieving a deck by ID."""
    deck_data = DeckCreate(name="Test Deck")
    created_deck = deck_dao.create(deck_data)

    retrieved_deck = deck_dao.get_by_id(created_deck.id)

    assert retrieved_deck is not None
    assert retrieved_deck.id == created_deck.id
    assert retrieved_deck.name == "Test Deck"


def test_get_deck_by_invalid_id(deck_dao):
    """Test retrieving a deck with invalid ID."""
    deck = deck_dao.get_by_id("invalid-id")

    assert deck is None


def test_get_all_decks(deck_dao):
    """Test retrieving all decks."""
    deck_dao.create(DeckCreate(name="Deck 1"))
    deck_dao.create(DeckCreate(name="Deck 2"))
    deck_dao.create(DeckCreate(name="Deck 3"))

    decks = deck_dao.get_all()

    assert len(decks) == 3
    assert {d.name for d in decks} == {"Deck 1", "Deck 2", "Deck 3"}


def test_update_last_studied(deck_dao):
    """Test updating last_studied timestamp."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))
    assert deck.last_studied is None

    deck_dao.update_last_studied(deck.id)

    updated_deck = deck_dao.get_by_id(deck.id)
    assert updated_deck.last_studied is not None


def test_delete_deck(deck_dao):
    """Test deleting a deck."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))

    result = deck_dao.delete(deck.id)
    assert result is True

    deleted_deck = deck_dao.get_by_id(deck.id)
    assert deleted_deck is None


# Flashcard DAO Tests
def test_create_flashcard(deck_dao, flashcard_dao):
    """Test creating a flashcard."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))
    flashcard_data = FlashcardCreate(
        question="What is Python?",
        answer="A programming language"
    )

    flashcard = flashcard_dao.create(deck.id, flashcard_data)

    assert flashcard.id is not None
    assert flashcard.deck_id == deck.id
    assert flashcard.question == "What is Python?"
    assert flashcard.answer == "A programming language"


def test_get_flashcard_by_id(deck_dao, flashcard_dao):
    """Test retrieving a flashcard by ID."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))
    flashcard_data = FlashcardCreate(question="Q1", answer="A1")
    created_flashcard = flashcard_dao.create(deck.id, flashcard_data)

    retrieved_flashcard = flashcard_dao.get_by_id(created_flashcard.id)

    assert retrieved_flashcard is not None
    assert retrieved_flashcard.id == created_flashcard.id


def test_get_flashcards_by_deck(deck_dao, flashcard_dao):
    """Test retrieving all flashcards for a deck."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))

    flashcard_dao.create(deck.id, FlashcardCreate(question="Q1", answer="A1"))
    flashcard_dao.create(deck.id, FlashcardCreate(question="Q2", answer="A2"))
    flashcard_dao.create(deck.id, FlashcardCreate(question="Q3", answer="A3"))

    flashcards = flashcard_dao.get_by_deck(deck.id)

    assert len(flashcards) == 3
    assert {fc.question for fc in flashcards} == {"Q1", "Q2", "Q3"}


def test_delete_flashcard(deck_dao, flashcard_dao):
    """Test deleting a flashcard."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))
    flashcard = flashcard_dao.create(deck.id, FlashcardCreate(question="Q1", answer="A1"))

    result = flashcard_dao.delete(flashcard.id)
    assert result is True

    deleted_flashcard = flashcard_dao.get_by_id(flashcard.id)
    assert deleted_flashcard is None


# Review DAO Tests
def test_create_review(deck_dao, flashcard_dao, review_dao):
    """Test creating a review."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))
    flashcard = flashcard_dao.create(deck.id, FlashcardCreate(question="Q1", answer="A1"))

    review_data = ReviewCreate(
        flashcard_id=flashcard.id,
        user_answer="My answer",
        ai_score=85,
        ai_grade="Good",
        ai_feedback="Well done!"
    )

    review = review_dao.create(review_data)

    assert review.id is not None
    assert review.flashcard_id == flashcard.id
    assert review.user_answer == "My answer"
    assert review.ai_score == 85
    assert review.ai_grade == "Good"


def test_get_reviews_by_flashcard(deck_dao, flashcard_dao, review_dao):
    """Test retrieving reviews for a flashcard."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))
    flashcard = flashcard_dao.create(deck.id, FlashcardCreate(question="Q1", answer="A1"))

    review_dao.create(ReviewCreate(
        flashcard_id=flashcard.id,
        user_answer="Answer 1",
        ai_score=70,
        ai_grade="Good",
        ai_feedback="Good job"
    ))
    review_dao.create(ReviewCreate(
        flashcard_id=flashcard.id,
        user_answer="Answer 2",
        ai_score=90,
        ai_grade="Perfect",
        ai_feedback="Excellent"
    ))

    reviews = review_dao.get_by_flashcard(flashcard.id)

    assert len(reviews) == 2
    # Should be ordered by reviewed_at descending (most recent first)
    assert reviews[0].ai_score == 90
    assert reviews[1].ai_score == 70


def test_get_deck_stats_empty(deck_dao, review_dao):
    """Test getting stats for an empty deck."""
    deck = deck_dao.create(DeckCreate(name="Empty Deck"))

    stats = review_dao.get_deck_stats(deck.id)

    assert stats.total_cards == 0
    assert stats.reviewed_cards == 0
    assert stats.average_score == 0.0


def test_get_deck_stats_with_reviews(deck_dao, flashcard_dao, review_dao):
    """Test getting stats for a deck with reviews."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))

    # Create flashcards
    fc1 = flashcard_dao.create(deck.id, FlashcardCreate(question="Q1", answer="A1"))
    fc2 = flashcard_dao.create(deck.id, FlashcardCreate(question="Q2", answer="A2"))
    flashcard_dao.create(deck.id, FlashcardCreate(question="Q3", answer="A3"))

    # Create reviews
    review_dao.create(ReviewCreate(
        flashcard_id=fc1.id, user_answer="A", ai_score=95, ai_grade="Perfect", ai_feedback="Great"
    ))
    review_dao.create(ReviewCreate(
        flashcard_id=fc2.id, user_answer="B", ai_score=75, ai_grade="Good", ai_feedback="Good"
    ))
    review_dao.create(ReviewCreate(
        flashcard_id=fc2.id, user_answer="C", ai_score=50, ai_grade="Partial", ai_feedback="OK"
    ))

    stats = review_dao.get_deck_stats(deck.id)

    assert stats.total_cards == 3
    assert stats.reviewed_cards == 2  # fc1 and fc2 have been reviewed
    assert stats.average_score == 73.33  # (95 + 75 + 50) / 3
    assert stats.perfect_count == 1
    assert stats.good_count == 1
    assert stats.partial_count == 1
    assert stats.wrong_count == 0


# Config DAO Tests
def test_set_and_get_config(config_dao):
    """Test setting and getting a config value."""
    config_dao.set("test_key", "test_value")

    value = config_dao.get("test_key")
    assert value == "test_value"


def test_get_config_with_default(config_dao):
    """Test getting config with default value."""
    value = config_dao.get("nonexistent_key", "default_value")
    assert value == "default_value"


def test_update_existing_config(config_dao):
    """Test updating an existing config value."""
    config_dao.set("key", "value1")
    config_dao.set("key", "value2")

    value = config_dao.get("key")
    assert value == "value2"


def test_get_all_config(config_dao):
    """Test getting all config values."""
    config_dao.set("key1", "value1")
    config_dao.set("key2", "value2")
    config_dao.set("key3", "value3")

    all_config = config_dao.get_all()

    assert len(all_config) == 3
    assert all_config["key1"] == "value1"
    assert all_config["key2"] == "value2"
    assert all_config["key3"] == "value3"


# Integration Tests
def test_cascade_delete_deck_with_flashcards(deck_dao, flashcard_dao):
    """Test that deleting a deck also deletes its flashcards."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))
    flashcard = flashcard_dao.create(deck.id, FlashcardCreate(question="Q1", answer="A1"))

    # Delete the deck
    deck_dao.delete(deck.id)

    # Flashcard should also be deleted
    deleted_flashcard = flashcard_dao.get_by_id(flashcard.id)
    assert deleted_flashcard is None


def test_cascade_delete_flashcard_with_reviews(deck_dao, flashcard_dao, review_dao):
    """Test that deleting a flashcard also deletes its reviews."""
    deck = deck_dao.create(DeckCreate(name="Test Deck"))
    flashcard = flashcard_dao.create(deck.id, FlashcardCreate(question="Q1", answer="A1"))
    review_dao.create(ReviewCreate(
        flashcard_id=flashcard.id,
        user_answer="A",
        ai_score=80,
        ai_grade="Good",
        ai_feedback="Good"
    ))

    # Delete the flashcard
    flashcard_dao.delete(flashcard.id)

    # Reviews should also be deleted
    reviews = review_dao.get_by_flashcard(flashcard.id)
    assert len(reviews) == 0
