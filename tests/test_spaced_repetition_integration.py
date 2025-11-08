"""
Integration tests for spaced repetition with database operations.
"""

from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time

from backend.database import Database, DeckDAO, FlashcardDAO, ReviewDAO
from backend.schemas import DeckCreate, FlashcardCreate, ReviewCreate
from backend.spaced_repetition import (
    SpacedRepetitionConfig,
    calculate_next_review,
    grade_from_ai_grade,
)


@pytest.fixture
def sample_deck_and_cards(test_db):
    """Create sample deck and flashcards for testing."""
    # Create deck
    deck_dao = DeckDAO(test_db)
    deck = deck_dao.create(DeckCreate(name="Test Spaced Repetition Deck"))

    # Create flashcards
    flashcard_dao = FlashcardDAO(test_db)
    cards = []
    for i in range(3):
        card = flashcard_dao.create(
            deck.id,
            FlashcardCreate(question=f"Test Question {i + 1}", answer=f"Test Answer {i + 1}"),
        )
        cards.append(card)

    return deck, cards, test_db


class TestSpacedRepetitionDatabaseIntegration:
    """Test spaced repetition integration with database operations."""

    @freeze_time("2025-01-15 12:00:00")
    def test_create_review_with_spaced_repetition_data(self, sample_deck_and_cards):
        """Test creating a review with spaced repetition fields."""
        _deck, cards, db = sample_deck_and_cards
        review_dao = ReviewDAO(db)

        # Create review with spaced repetition data
        review_data = ReviewCreate(
            flashcard_id=cards[0].id,
            user_answer="Test user answer",
            ai_score=85,
            ai_grade="Good",
            ai_feedback="Good answer with minor improvements needed",
            next_review_date=datetime(2025, 1, 16, 12, 0, 0),
            ease_factor=2.5,
            interval_days=1,
            repetitions=1,
        )

        review = review_dao.create(review_data)

        # Verify all spaced repetition fields are saved correctly
        assert review.ease_factor == 2.5
        assert review.interval_days == 1
        assert review.repetitions == 1
        # Note: Database may not preserve timezone, so compare without timezone
        expected_date = datetime(2025, 1, 16, 12, 0, 0)
        assert review.next_review_date == expected_date or review.next_review_date == datetime(
            2025, 1, 16, 12, 0, 0, tzinfo=UTC
        )

    @freeze_time("2025-01-15 12:00:00")
    def test_due_cards_count_calculation(self, sample_deck_and_cards):
        """Test calculating due cards count."""
        deck, cards, db = sample_deck_and_cards
        review_dao = ReviewDAO(db)

        # Initially, all cards should be due (no reviews)
        due_count = review_dao.get_due_cards_count(deck.id)
        assert due_count == 3

        # Add a review for one card that's due tomorrow
        review_dao.create(
            ReviewCreate(
                flashcard_id=cards[0].id,
                user_answer="Test answer",
                ai_score=85,
                ai_grade="Good",
                ai_feedback="Good answer",
                next_review_date=datetime(2025, 1, 16, 12, 0, 0, tzinfo=UTC),  # Due tomorrow
                ease_factor=2.5,
                interval_days=1,
                repetitions=1,
            )
        )

        # Should have 2 due cards (two never reviewed, one due tomorrow is NOT due yet)
        due_count = review_dao.get_due_cards_count(deck.id)
        assert due_count == 2

        # Add a review for another card that's due in the future
        review_dao.create(
            ReviewCreate(
                flashcard_id=cards[1].id,
                user_answer="Test answer",
                ai_score=95,
                ai_grade="Perfect",
                ai_feedback="Perfect answer",
                next_review_date=datetime(2025, 1, 20, 12, 0, 0, tzinfo=UTC),  # Due in 5 days
                ease_factor=2.65,
                interval_days=5,
                repetitions=1,
            )
        )

        # Should now have 1 due card (one never reviewed, two with future review dates)
        due_count = review_dao.get_due_cards_count(deck.id)
        assert due_count == 1

    @freeze_time("2025-01-15 12:00:00")
    def test_get_due_flashcards(self, sample_deck_and_cards):
        """Test getting list of due flashcards."""
        deck, cards, db = sample_deck_and_cards
        review_dao = ReviewDAO(db)

        # Initially, all cards should be due
        due_cards = review_dao.get_due_flashcards(deck.id)
        assert len(due_cards) == 3
        due_card_ids = [card.id for card in due_cards]
        assert cards[0].id in due_card_ids
        assert cards[1].id in due_card_ids
        assert cards[2].id in due_card_ids

        # Add review for one card making it not due
        review_dao.create(
            ReviewCreate(
                flashcard_id=cards[0].id,
                user_answer="Test answer",
                ai_score=85,
                ai_grade="Good",
                ai_feedback="Good answer",
                next_review_date=datetime(2025, 1, 20, 12, 0, 0, tzinfo=UTC),  # Due in future
                ease_factor=2.5,
                interval_days=5,
                repetitions=1,
            )
        )

        # Should now have 2 due cards
        due_cards = review_dao.get_due_flashcards(deck.id)
        assert len(due_cards) == 2
        due_card_ids = [card.id for card in due_cards]
        assert cards[0].id not in due_card_ids
        assert cards[1].id in due_card_ids
        assert cards[2].id in due_card_ids

    @freeze_time("2025-01-15 12:00:00")
    def test_deck_stats_include_due_cards(self, sample_deck_and_cards):
        """Test that deck stats include due cards count."""
        deck, cards, db = sample_deck_and_cards
        review_dao = ReviewDAO(db)

        # Get initial stats
        stats = review_dao.get_deck_stats(deck.id)
        assert stats.total_cards == 3
        assert stats.due_cards == 3  # All cards due initially

        # Add reviews with different due dates
        review_dao.create(
            ReviewCreate(
                flashcard_id=cards[0].id,
                user_answer="Test answer 1",
                ai_score=85,
                ai_grade="Good",
                ai_feedback="Good answer",
                next_review_date=datetime(2025, 1, 14, 12, 0, 0, tzinfo=UTC),  # Due yesterday
                ease_factor=2.5,
                interval_days=1,
                repetitions=1,
            )
        )

        review_dao.create(
            ReviewCreate(
                flashcard_id=cards[1].id,
                user_answer="Test answer 2",
                ai_score=95,
                ai_grade="Perfect",
                ai_feedback="Perfect answer",
                next_review_date=datetime(2025, 1, 16, 12, 0, 0, tzinfo=UTC),  # Due tomorrow
                ease_factor=2.65,
                interval_days=1,
                repetitions=1,
            )
        )

        review_dao.create(
            ReviewCreate(
                flashcard_id=cards[2].id,
                user_answer="Test answer 3",
                ai_score=75,
                ai_grade="Partial",
                ai_feedback="Partial answer",
                next_review_date=datetime(2025, 1, 20, 12, 0, 0, tzinfo=UTC),  # Due in future
                ease_factor=2.3,
                interval_days=5,
                repetitions=0,
            )
        )

        # Get updated stats
        stats = review_dao.get_deck_stats(deck.id)
        assert stats.total_cards == 3
        assert stats.reviewed_cards == 3
        assert stats.due_cards == 1  # Only one due yesterday (tomorrow is not due yet)

    @freeze_time("2025-01-15 12:00:00")
    def test_get_latest_reviews_by_deck(self, sample_deck_and_cards):
        """Test getting latest reviews for each card in a deck."""
        deck, cards, db = sample_deck_and_cards
        review_dao = ReviewDAO(db)

        # Add multiple reviews for same card
        review_dao.create(
            ReviewCreate(
                flashcard_id=cards[0].id,
                user_answer="First answer",
                ai_score=60,
                ai_grade="Wrong",
                ai_feedback="Wrong answer",
                next_review_date=datetime(2025, 1, 16, 12, 0, 0, tzinfo=UTC),
                ease_factor=2.3,
                interval_days=1,
                repetitions=0,
            )
        )

        # Simulate time passing
        with freeze_time("2025-01-16 12:00:00"):
            review_dao.create(
                ReviewCreate(
                    flashcard_id=cards[0].id,
                    user_answer="Second answer",
                    ai_score=85,
                    ai_grade="Good",
                    ai_feedback="Better answer",
                    next_review_date=datetime(2025, 1, 17, 12, 0, 0, tzinfo=UTC),
                    ease_factor=2.3,
                    interval_days=1,
                    repetitions=1,
                )
            )

        # Add review for another card
        review_dao.create(
            ReviewCreate(
                flashcard_id=cards[1].id,
                user_answer="Test answer",
                ai_score=95,
                ai_grade="Perfect",
                ai_feedback="Perfect answer",
                next_review_date=datetime(2025, 1, 20, 12, 0, 0, tzinfo=UTC),
                ease_factor=2.65,
                interval_days=5,
                repetitions=1,
            )
        )

        # Get latest reviews
        latest_reviews = review_dao.get_latest_reviews_by_deck(deck.id)

        # Should get latest review for each card that has reviews
        assert len(latest_reviews) == 2

        # Find reviews by flashcard_id
        review_by_card = {review.flashcard_id: review for review in latest_reviews}

        # Check latest review for cards[0] is the second (better) one
        card0_review = review_by_card[cards[0].id]
        assert card0_review.user_answer == "Second answer"
        assert card0_review.ai_score == 85
        assert card0_review.repetitions == 1

        # Check review for cards[1]
        card1_review = review_by_card[cards[1].id]
        assert card1_review.user_answer == "Test answer"
        assert card1_review.ai_score == 95
        assert card1_review.repetitions == 1


class TestSpacedRepetitionWorkflowIntegration:
    """Test complete spaced repetition workflows with database."""

    @freeze_time("2025-01-15 12:00:00")
    def test_complete_study_session_workflow(self, sample_deck_and_cards):
        """Test a complete study session with spaced repetition."""
        deck, cards, db = sample_deck_and_cards
        review_dao = ReviewDAO(db)
        config = SpacedRepetitionConfig()

        # Simulate first study session for card
        card = cards[0]

        # First review: User gets "Good" grade
        grade = grade_from_ai_grade("Good")
        sr_result = calculate_next_review(
            grade=grade,
            current_ease_factor=2.5,  # Default for new card
            current_interval_days=1,  # Default for new card
            current_repetitions=0,  # New card
            config=config,
        )

        # Save first review
        review1 = review_dao.create(
            ReviewCreate(
                flashcard_id=card.id,
                user_answer="My first answer",
                ai_score=80,
                ai_grade="Good",
                ai_feedback="Good understanding shown",
                next_review_date=sr_result.next_review_date,
                ease_factor=sr_result.ease_factor,
                interval_days=sr_result.interval_days,
                repetitions=sr_result.repetitions,
            )
        )

        assert review1.repetitions == 1
        assert review1.ease_factor == 2.5
        assert review1.interval_days == 1

        # Fast forward to next review date
        with freeze_time("2025-01-16 12:00:00"):
            # Card should be due now
            due_cards = review_dao.get_due_flashcards(deck.id)
            due_card_ids = [card.id for card in due_cards]
            assert card.id in due_card_ids

            # Second review: User gets "Perfect" grade
            grade = grade_from_ai_grade("Perfect")
            sr_result = calculate_next_review(
                grade=grade,
                current_ease_factor=review1.ease_factor,
                current_interval_days=review1.interval_days,
                current_repetitions=review1.repetitions,
                config=config,
            )

            # Save second review
            review2 = review_dao.create(
                ReviewCreate(
                    flashcard_id=card.id,
                    user_answer="My improved answer",
                    ai_score=95,
                    ai_grade="Perfect",
                    ai_feedback="Excellent mastery demonstrated",
                    next_review_date=sr_result.next_review_date,
                    ease_factor=sr_result.ease_factor,
                    interval_days=sr_result.interval_days,
                    repetitions=sr_result.repetitions,
                )
            )

            assert review2.repetitions == 2
            assert review2.ease_factor > review1.ease_factor  # Increased for perfect
            assert review2.interval_days >= review1.interval_days  # Longer interval

            # Card should no longer be due
            due_cards = review_dao.get_due_flashcards(deck.id)
            due_card_ids = [card.id for card in due_cards]
            assert card.id not in due_card_ids

    @freeze_time("2025-01-15 12:00:00")
    def test_learning_progression_with_setbacks(self, sample_deck_and_cards):
        """Test learning progression that includes wrong answers."""
        _deck, cards, db = sample_deck_and_cards
        review_dao = ReviewDAO(db)
        config = SpacedRepetitionConfig()

        card = cards[0]

        # First review: Good
        grade = grade_from_ai_grade("Good")
        sr_result = calculate_next_review(
            grade=grade,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=0,
            config=config,
        )

        review1 = review_dao.create(
            ReviewCreate(
                flashcard_id=card.id,
                user_answer="First answer",
                ai_score=80,
                ai_grade="Good",
                ai_feedback="Good understanding",
                next_review_date=sr_result.next_review_date,
                ease_factor=sr_result.ease_factor,
                interval_days=sr_result.interval_days,
                repetitions=sr_result.repetitions,
            )
        )

        # Fast forward and do second review: Wrong
        with freeze_time("2025-01-16 12:00:00"):
            grade = grade_from_ai_grade("Wrong")
            sr_result = calculate_next_review(
                grade=grade,
                current_ease_factor=review1.ease_factor,
                current_interval_days=review1.interval_days,
                current_repetitions=review1.repetitions,
                config=config,
            )

            review2 = review_dao.create(
                ReviewCreate(
                    flashcard_id=card.id,
                    user_answer="Wrong answer",
                    ai_score=30,
                    ai_grade="Wrong",
                    ai_feedback="Incorrect understanding",
                    next_review_date=sr_result.next_review_date,
                    ease_factor=sr_result.ease_factor,
                    interval_days=sr_result.interval_days,
                    repetitions=sr_result.repetitions,
                )
            )

            # Should reset repetitions and decrease ease factor
            assert review2.repetitions == 0
            assert review2.ease_factor < review1.ease_factor
            assert review2.interval_days == config.initial_interval_days

            # Card should still be due soon
            expected_date = datetime(2025, 1, 17, 12, 0, 0)
            assert (
                review2.next_review_date == expected_date
                or review2.next_review_date == datetime(2025, 1, 17, 12, 0, 0, tzinfo=UTC)
            )

        # Fast forward and do third review: Good (recovery)
        with freeze_time("2025-01-17 12:00:00"):
            grade = grade_from_ai_grade("Good")
            sr_result = calculate_next_review(
                grade=grade,
                current_ease_factor=review2.ease_factor,
                current_interval_days=review2.interval_days,
                current_repetitions=review2.repetitions,
                config=config,
            )

            review3 = review_dao.create(
                ReviewCreate(
                    flashcard_id=card.id,
                    user_answer="Corrected answer",
                    ai_score=85,
                    ai_grade="Good",
                    ai_feedback="Much better understanding",
                    next_review_date=sr_result.next_review_date,
                    ease_factor=sr_result.ease_factor,
                    interval_days=sr_result.interval_days,
                    repetitions=sr_result.repetitions,
                )
            )

            # Should start building up again
            assert review3.repetitions == 1
            assert review3.ease_factor == review2.ease_factor  # Unchanged for good
            assert review3.interval_days == config.initial_interval_days

    def test_deck_with_no_cards_due_count(self, test_db):
        """Test due cards count for deck with no cards."""
        deck_dao = DeckDAO(test_db)
        deck = deck_dao.create(DeckCreate(name="Empty Deck"))

        review_dao = ReviewDAO(test_db)
        due_count = review_dao.get_due_cards_count(deck.id)
        assert due_count == 0

        due_cards = review_dao.get_due_flashcards(deck.id)
        assert len(due_cards) == 0

    def test_time_progression_simulation(self, sample_deck_and_cards):
        """Test spaced repetition over multiple days."""
        deck, cards, db = sample_deck_and_cards
        review_dao = ReviewDAO(db)
        config = SpacedRepetitionConfig()

        card = cards[0]

        # Day 1: First review
        with freeze_time("2025-01-15 12:00:00"):
            grade = grade_from_ai_grade("Good")
            sr_result = calculate_next_review(
                grade=grade,
                current_ease_factor=2.5,
                current_interval_days=1,
                current_repetitions=0,
                config=config,
            )

            review1 = review_dao.create(
                ReviewCreate(
                    flashcard_id=card.id,
                    user_answer="Day 1 answer",
                    ai_score=80,
                    ai_grade="Good",
                    ai_feedback="Good start",
                    next_review_date=sr_result.next_review_date,
                    ease_factor=sr_result.ease_factor,
                    interval_days=sr_result.interval_days,
                    repetitions=sr_result.repetitions,
                )
            )

        # Day 2: Second review
        with freeze_time("2025-01-16 12:00:00"):
            # Verify card is due
            assert review_dao.get_due_cards_count(deck.id) == 3  # This card + 2 unreviewed

            grade = grade_from_ai_grade("Perfect")
            sr_result = calculate_next_review(
                grade=grade,
                current_ease_factor=review1.ease_factor,
                current_interval_days=review1.interval_days,
                current_repetitions=review1.repetitions,
                config=config,
            )

            review2 = review_dao.create(
                ReviewCreate(
                    flashcard_id=card.id,
                    user_answer="Day 2 improved answer",
                    ai_score=95,
                    ai_grade="Perfect",
                    ai_feedback="Excellent improvement",
                    next_review_date=sr_result.next_review_date,
                    ease_factor=sr_result.ease_factor,
                    interval_days=sr_result.interval_days,
                    repetitions=sr_result.repetitions,
                )
            )

        # Day 3: Card should not be due yet
        with freeze_time("2025-01-17 12:00:00"):
            assert review_dao.get_due_cards_count(deck.id) == 2  # Only 2 unreviewed cards

        # Fast forward to when card is due again
        future_date = review2.next_review_date.replace(tzinfo=None)
        with freeze_time(future_date):
            assert review_dao.get_due_cards_count(deck.id) == 3  # Card is due again + 2 unreviewed
