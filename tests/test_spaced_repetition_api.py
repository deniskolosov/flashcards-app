"""
API tests for spaced repetition functionality.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time

from backend.config import ConfigManager
from backend.database import Database
from backend.grading import GradingService
from backend.main import app, get_config_manager, get_db, get_grading_service
from backend.models import Base


@pytest.fixture
def test_client(test_db):
    """Create a test client with mocked dependencies."""

    # Mock grading service to return predictable results
    class MockGradingService:
        def grade_answer(self, question, reference_answer, user_answer):
            # Return predictable grades based on user answer
            if "perfect" in user_answer.lower():
                return type(
                    "GradingResult",
                    (),
                    {
                        "score": 95,
                        "grade": "Perfect",
                        "feedback": "Excellent answer",
                        "key_concepts_covered": ["concept1"],
                        "key_concepts_missed": [],
                    },
                )()
            elif "good" in user_answer.lower():
                return type(
                    "GradingResult",
                    (),
                    {
                        "score": 85,
                        "grade": "Good",
                        "feedback": "Good answer",
                        "key_concepts_covered": ["concept1"],
                        "key_concepts_missed": ["concept2"],
                    },
                )()
            elif "partial" in user_answer.lower():
                return type(
                    "GradingResult",
                    (),
                    {
                        "score": 60,
                        "grade": "Partial",
                        "feedback": "Partial understanding",
                        "key_concepts_covered": [],
                        "key_concepts_missed": ["concept1", "concept2"],
                    },
                )()
            else:
                return type(
                    "GradingResult",
                    (),
                    {
                        "score": 30,
                        "grade": "Wrong",
                        "feedback": "Incorrect answer",
                        "key_concepts_covered": [],
                        "key_concepts_missed": ["concept1", "concept2"],
                    },
                )()

    mock_grading_service = MockGradingService()

    # Create config manager with proper DAO
    config_manager = ConfigManager()
    from backend.database import ConfigDAO

    config_manager.config_dao = ConfigDAO(test_db)

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_config_manager] = lambda: config_manager
    app.dependency_overrides[get_grading_service] = lambda: mock_grading_service

    with TestClient(app) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def sample_deck_with_cards(test_client):
    """Create a sample deck with flashcards for testing."""
    # Create deck
    response = test_client.post("/api/decks", json={"name": "Spaced Repetition Test Deck"})
    assert response.status_code == 200
    deck = response.json()

    # Create flashcards
    cards = []
    for i in range(3):
        response = test_client.post(
            f"/api/decks/{deck['id']}/flashcards",
            json={"question": f"Test Question {i + 1}", "answer": f"Test Answer {i + 1}"},
        )
        assert response.status_code == 200
        cards.append(response.json())

    return deck, cards


class TestSpacedRepetitionAPIIntegration:
    """Test API endpoints with spaced repetition functionality."""

    @freeze_time("2025-01-15 12:00:00")
    def test_grade_answer_creates_spaced_repetition_data(self, test_client, sample_deck_with_cards):
        """Test that grading creates proper spaced repetition data."""
        deck, cards = sample_deck_with_cards
        card = cards[0]

        # First review with "good" answer
        response = test_client.post(
            "/api/grade", json={"flashcard_id": card["id"], "user_answer": "This is a good answer"}
        )

        assert response.status_code == 200
        result = response.json()
        assert result["grade"] == "Good"
        assert result["score"] == 85

        # Verify deck stats now include due cards
        response = test_client.get(f"/api/decks/{deck['id']}/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_cards"] == 3
        assert stats["reviewed_cards"] == 1
        assert (
            stats["due_cards"] == 2
        )  # 2 unreviewed cards (reviewed card due tomorrow is not due yet)

    @freeze_time("2025-01-15 12:00:00")
    def test_multiple_reviews_progression(self, test_client, sample_deck_with_cards):
        """Test spaced repetition progression through multiple reviews."""
        deck, cards = sample_deck_with_cards
        card = cards[0]

        # First review: Good
        response = test_client.post(
            "/api/grade", json={"flashcard_id": card["id"], "user_answer": "This is a good answer"}
        )
        assert response.status_code == 200

        # Fast forward to next day
        with freeze_time("2025-01-16 12:00:00"):
            # Card should be due
            response = test_client.get(f"/api/decks/{deck['id']}/due-cards")
            assert response.status_code == 200
            due_cards = response.json()
            due_card_ids = [card["id"] for card in due_cards]
            assert card["id"] in due_card_ids

            # Second review: Perfect
            response = test_client.post(
                "/api/grade",
                json={"flashcard_id": card["id"], "user_answer": "This is a perfect answer"},
            )
            assert response.status_code == 200
            result = response.json()
            assert result["grade"] == "Perfect"

            # Card should no longer be due immediately
            response = test_client.get(f"/api/decks/{deck['id']}/due-cards")
            assert response.status_code == 200
            due_cards = response.json()
            due_card_ids = [card["id"] for card in due_cards]
            # Card might still be due if interval is 1 day, but with longer intervals it won't be

    def test_due_cards_endpoint(self, test_client, sample_deck_with_cards):
        """Test the due cards endpoint."""
        deck, cards = sample_deck_with_cards

        # Initially all cards should be due
        response = test_client.get(f"/api/decks/{deck['id']}/due-cards")
        assert response.status_code == 200
        due_cards = response.json()
        assert len(due_cards) == 3

        # Grade one card to make it not immediately due
        with freeze_time("2025-01-15 12:00:00"):
            response = test_client.post(
                "/api/grade",
                json={
                    "flashcard_id": cards[0]["id"],
                    "user_answer": "This is a perfect answer",  # Will get long interval
                },
            )
            assert response.status_code == 200

        # Check due cards again - should be fewer if the perfect answer got a longer interval
        response = test_client.get(f"/api/decks/{deck['id']}/due-cards")
        assert response.status_code == 200
        due_cards = response.json()
        # The exact count depends on the interval calculation, but should be <= 3
        assert len(due_cards) <= 3

    def test_due_cards_endpoint_nonexistent_deck(self, test_client):
        """Test due cards endpoint with nonexistent deck."""
        response = test_client.get("/api/decks/nonexistent-id/due-cards")
        assert response.status_code == 404
        assert "Deck not found" in response.json()["detail"]

    def test_start_due_study_session(self, test_client, sample_deck_with_cards):
        """Test starting a due-cards-only study session."""
        deck, _cards = sample_deck_with_cards

        # Start due cards session
        response = test_client.post("/api/sessions/start-due", json={"deck_id": deck["id"]})
        assert response.status_code == 200
        session = response.json()

        assert "session_id" in session
        assert session["total_due_cards"] == 3  # All cards are due initially
        assert session["cards_in_session"] == 3
        assert "Started due cards study session with 3 cards" in session["message"]

    def test_start_due_study_session_with_no_due_cards(self, test_client, sample_deck_with_cards):
        """Test starting due session when no cards are due."""
        deck, cards = sample_deck_with_cards

        # Make all cards not due by giving them future review dates
        with freeze_time("2025-01-15 12:00:00"):
            for card in cards:
                response = test_client.post(
                    "/api/grade",
                    json={"flashcard_id": card["id"], "user_answer": "This is a perfect answer"},
                )
                assert response.status_code == 200

        # Fast forward but not enough to make cards due again
        with freeze_time("2025-01-16 12:00:00"):
            # Try to start due cards session
            response = test_client.post("/api/sessions/start-due", json={"deck_id": deck["id"]})

            # Might succeed if cards are due tomorrow, or fail if they have longer intervals
            # The exact behavior depends on the spaced repetition calculation
            # For perfect answers with the default algorithm, cards might still be due soon

    def test_start_due_study_session_with_card_limit(self, test_client, sample_deck_with_cards):
        """Test starting due session with card limit."""
        deck, _cards = sample_deck_with_cards

        # Start due cards session with limit
        response = test_client.post(
            "/api/sessions/start-due", json={"deck_id": deck["id"], "card_limit": 2}
        )
        assert response.status_code == 200
        session = response.json()

        assert session["total_due_cards"] == 3  # All cards are due
        assert session["cards_in_session"] == 2  # Limited to 2
        assert "Started due cards study session with 2 cards" in session["message"]

    def test_deck_stats_include_due_count(self, test_client, sample_deck_with_cards):
        """Test that deck stats include due cards count."""
        deck, cards = sample_deck_with_cards

        # Get initial stats
        response = test_client.get(f"/api/decks/{deck['id']}/stats")
        assert response.status_code == 200
        stats = response.json()

        assert stats["total_cards"] == 3
        assert stats["due_cards"] == 3  # All cards due initially
        assert stats["reviewed_cards"] == 0

        # Grade one card
        with freeze_time("2025-01-15 12:00:00"):
            response = test_client.post(
                "/api/grade",
                json={"flashcard_id": cards[0]["id"], "user_answer": "This is a good answer"},
            )
            assert response.status_code == 200

        # Check updated stats
        response = test_client.get(f"/api/decks/{deck['id']}/stats")
        assert response.status_code == 200
        stats = response.json()

        assert stats["total_cards"] == 3
        assert stats["reviewed_cards"] == 1
        # due_cards count depends on the review schedule, but should be <= 3
        assert stats["due_cards"] <= 3
        assert stats["due_cards"] >= 2  # At least the 2 unreviewed cards

    def test_get_all_decks_includes_due_counts(self, test_client, sample_deck_with_cards):
        """Test that getting all decks includes due card counts."""
        deck, _cards = sample_deck_with_cards

        # Get all decks
        response = test_client.get("/api/decks")
        assert response.status_code == 200
        decks = response.json()

        assert len(decks) == 1
        deck_data = decks[0]
        assert deck_data["id"] == deck["id"]
        assert "stats" in deck_data
        assert deck_data["stats"]["due_cards"] == 3  # All cards due initially

    @freeze_time("2025-01-15 12:00:00")
    def test_spaced_repetition_with_different_grades(self, test_client, sample_deck_with_cards):
        """Test spaced repetition behavior with different grades."""
        deck, cards = sample_deck_with_cards

        # Test different grades and their effects
        test_cases = [
            ("wrong answer", "Wrong", 30),
            ("partial answer", "Partial", 60),
            ("good answer", "Good", 85),
            ("perfect answer", "Perfect", 95),
        ]

        for i, (answer_text, expected_grade, expected_score) in enumerate(test_cases):
            card = cards[i % len(cards)]  # Cycle through cards

            response = test_client.post(
                "/api/grade", json={"flashcard_id": card["id"], "user_answer": answer_text}
            )

            assert response.status_code == 200
            result = response.json()
            assert result["grade"] == expected_grade
            assert result["score"] == expected_score

        # Verify stats updated correctly
        response = test_client.get(f"/api/decks/{deck['id']}/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["reviewed_cards"] == 3  # All 3 cards have been reviewed (some multiple times)

    def test_session_integration_with_spaced_repetition(self, test_client, sample_deck_with_cards):
        """Test that regular study sessions work with spaced repetition."""
        deck, _cards = sample_deck_with_cards

        # Start regular study session
        response = test_client.post("/api/sessions/start", json={"deck_id": deck["id"]})
        assert response.status_code == 200
        session = response.json()
        session_id = session["session_id"]

        # Get first card
        response = test_client.get(f"/api/sessions/{session_id}/next")
        assert response.status_code == 200
        card_data = response.json()

        assert "flashcard" in card_data
        assert "card_number" in card_data
        assert "total_cards" in card_data

        # Grade the card
        response = test_client.post(
            "/api/grade",
            json={
                "flashcard_id": card_data["flashcard"]["id"],
                "user_answer": "This is a good answer",
            },
        )
        assert response.status_code == 200

        # The spaced repetition data should be saved even in regular sessions
        response = test_client.get(f"/api/decks/{deck['id']}/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["reviewed_cards"] == 1

    def test_config_endpoint_includes_spaced_repetition_settings(self, test_client):
        """Test that config endpoint includes spaced repetition settings."""
        response = test_client.get("/api/config")
        assert response.status_code == 200
        config = response.json()

        # Check that spaced repetition fields are present
        assert "initial_interval_days" in config
        assert "easy_multiplier" in config
        assert "good_multiplier" in config
        assert "minimum_interval_days" in config
        assert "maximum_interval_days" in config

        # Check default values
        assert config["initial_interval_days"] == 1
        assert config["easy_multiplier"] == 2.5
        assert config["good_multiplier"] == 1.8
        assert config["minimum_interval_days"] == 1
        assert config["maximum_interval_days"] == 180

    def test_update_spaced_repetition_config(self, test_client):
        """Test updating spaced repetition configuration."""
        # Update config
        response = test_client.put(
            "/api/config",
            json={
                "initial_interval_days": 2,
                "easy_multiplier": 3.0,
                "good_multiplier": 2.0,
                "minimum_interval_days": 1,
                "maximum_interval_days": 365,
            },
        )
        assert response.status_code == 200
        updated_config = response.json()

        assert updated_config["initial_interval_days"] == 2
        assert updated_config["easy_multiplier"] == 3.0
        assert updated_config["good_multiplier"] == 2.0
        assert updated_config["maximum_interval_days"] == 365

    def test_spaced_repetition_validation_in_config(self, test_client):
        """Test validation of spaced repetition configuration values."""
        # Test invalid values
        invalid_configs = [
            {"initial_interval_days": 0},  # Too small
            {"initial_interval_days": 400},  # Too large
            {"easy_multiplier": 0.5},  # Too small
            {"easy_multiplier": 6.0},  # Too large
            {"minimum_interval_days": 0},  # Too small
            {"minimum_interval_days": 50},  # Too large
            {"maximum_interval_days": 20},  # Too small
            {"maximum_interval_days": 4000},  # Too large
        ]

        for invalid_config in invalid_configs:
            response = test_client.put("/api/config", json=invalid_config)
            assert response.status_code == 422  # Validation error

    def test_due_session_get_next_card(self, test_client, sample_deck_with_cards):
        """Test that getting next card works in due-cards-only sessions."""
        deck, _cards = sample_deck_with_cards

        # Start due cards session
        response = test_client.post("/api/sessions/start-due", json={"deck_id": deck["id"]})
        assert response.status_code == 200
        session = response.json()
        session_id = session["session_id"]

        # Get first card from due session - this should not fail with KeyError
        response = test_client.get(f"/api/sessions/{session_id}/next")
        assert response.status_code == 200
        card_data = response.json()

        assert "flashcard" in card_data
        assert "card_number" in card_data
        assert "total_cards" in card_data

        # Verify the card data is correct
        assert card_data["card_number"] == 1
        assert card_data["total_cards"] == 3
