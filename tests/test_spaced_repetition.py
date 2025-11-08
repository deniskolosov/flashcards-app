"""
Tests for spaced repetition functionality.
"""

from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time

from backend.spaced_repetition import (
    Grade,
    SpacedRepetitionConfig,
    calculate_next_review,
    get_due_cards_count,
    grade_from_ai_grade,
    is_card_due,
)


class TestGradeConversion:
    """Test grade conversion from AI strings to Grade enum."""

    def test_grade_from_ai_grade_perfect(self):
        assert grade_from_ai_grade("Perfect") == Grade.PERFECT

    def test_grade_from_ai_grade_good(self):
        assert grade_from_ai_grade("Good") == Grade.GOOD

    def test_grade_from_ai_grade_partial(self):
        assert grade_from_ai_grade("Partial") == Grade.PARTIAL

    def test_grade_from_ai_grade_wrong(self):
        assert grade_from_ai_grade("Wrong") == Grade.WRONG

    def test_grade_from_ai_grade_unknown_defaults_to_wrong(self):
        assert grade_from_ai_grade("Unknown") == Grade.WRONG
        assert grade_from_ai_grade("") == Grade.WRONG
        assert grade_from_ai_grade("invalid") == Grade.WRONG


class TestSpacedRepetitionConfig:
    """Test SpacedRepetitionConfig default values."""

    def test_default_config_values(self):
        config = SpacedRepetitionConfig()
        assert config.initial_interval_days == 1
        assert config.easy_multiplier == 2.5
        assert config.good_multiplier == 1.8
        assert config.minimum_interval_days == 1
        assert config.maximum_interval_days == 180
        assert config.ease_factor_minimum == 1.3
        assert config.ease_factor_maximum == 3.0
        assert config.ease_factor_decrease == 0.2
        assert config.ease_factor_increase == 0.15

    def test_custom_config_values(self):
        config = SpacedRepetitionConfig(
            initial_interval_days=2,
            easy_multiplier=3.0,
            good_multiplier=2.0,
            minimum_interval_days=2,
            maximum_interval_days=365,
        )
        assert config.initial_interval_days == 2
        assert config.easy_multiplier == 3.0
        assert config.good_multiplier == 2.0
        assert config.minimum_interval_days == 2
        assert config.maximum_interval_days == 365


@freeze_time("2025-01-15 12:00:00")
class TestCalculateNextReview:
    """Test the core spaced repetition algorithm."""

    def test_new_card_perfect_grade(self):
        """Test first review with Perfect grade."""
        config = SpacedRepetitionConfig()
        result = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=0,
            config=config,
        )

        # First repetition: should use initial interval
        assert result.repetitions == 1
        assert result.interval_days == 1
        assert result.ease_factor == 2.5 + 0.15  # Increased for perfect
        assert result.next_review_date == datetime(2025, 1, 16, 12, 0, 0)

    def test_new_card_good_grade(self):
        """Test first review with Good grade."""
        config = SpacedRepetitionConfig()
        result = calculate_next_review(
            Grade.GOOD,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=0,
            config=config,
        )

        # First repetition: should use initial interval
        assert result.repetitions == 1
        assert result.interval_days == 1
        assert result.ease_factor == 2.5  # Unchanged for good
        assert result.next_review_date == datetime(2025, 1, 16, 12, 0, 0)

    def test_new_card_partial_grade(self):
        """Test first review with Partial grade."""
        config = SpacedRepetitionConfig()
        result = calculate_next_review(
            Grade.PARTIAL,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=0,
            config=config,
        )

        # Partial: repetitions reset, ease factor decreased, interval halved
        assert result.repetitions == 0
        assert result.interval_days == 1  # max(1, 1//2) = 1
        assert result.ease_factor == 2.3  # 2.5 - 0.2, but >= 1.3
        assert result.next_review_date == datetime(2025, 1, 16, 12, 0, 0)

    def test_new_card_wrong_grade(self):
        """Test first review with Wrong grade."""
        config = SpacedRepetitionConfig()
        result = calculate_next_review(
            Grade.WRONG,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=0,
            config=config,
        )

        # Wrong: everything resets
        assert result.repetitions == 0
        assert result.interval_days == 1  # Reset to initial
        assert result.ease_factor == 2.3  # 2.5 - 0.2
        assert result.next_review_date == datetime(2025, 1, 16, 12, 0, 0)

    def test_second_review_good_grade(self):
        """Test second review with Good grade."""
        config = SpacedRepetitionConfig()
        result = calculate_next_review(
            Grade.GOOD,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=1,  # Second review
            config=config,
        )

        # Second repetition: should use good_multiplier
        assert result.repetitions == 2
        assert result.interval_days == int(1 * 1.8)  # 1
        assert result.ease_factor == 2.5
        assert result.next_review_date == datetime(2025, 1, 16, 12, 0, 0)

    def test_second_review_perfect_grade(self):
        """Test second review with Perfect grade."""
        config = SpacedRepetitionConfig()
        result = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=1,  # Second review
            config=config,
        )

        # Second repetition with Perfect: should use easy_multiplier
        assert result.repetitions == 2
        assert result.interval_days == int(1 * 2.5)  # 2
        assert result.ease_factor == 2.5 + 0.15  # Increased
        assert result.next_review_date == datetime(2025, 1, 17, 12, 0, 0)

    def test_third_review_good_grade(self):
        """Test third review with Good grade (uses ease factor)."""
        config = SpacedRepetitionConfig()
        result = calculate_next_review(
            Grade.GOOD,
            current_ease_factor=2.5,
            current_interval_days=3,
            current_repetitions=2,  # Third+ review
            config=config,
        )

        # Third+ repetition: should use ease factor
        assert result.repetitions == 3
        assert result.interval_days == int(3 * 2.5)  # 7
        assert result.ease_factor == 2.5
        assert result.next_review_date == datetime(2025, 1, 22, 12, 0, 0)

    def test_third_review_perfect_grade(self):
        """Test third review with Perfect grade."""
        config = SpacedRepetitionConfig()
        result = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.5,
            current_interval_days=3,
            current_repetitions=2,  # Third+ review
            config=config,
        )

        # Third+ repetition with Perfect: ease factor * easy/good ratio
        assert result.repetitions == 3
        # Ease factor increases to 2.65, then calculation: 3 * 2.65 * 2.5 / 1.8 = ~11
        expected_interval = int(3 * 2.65 * 2.5 / 1.8)  # ~11
        assert result.interval_days == expected_interval
        assert result.ease_factor == 2.5 + 0.15
        expected_date = datetime(2025, 1, 15, 12, 0, 0) + timedelta(
            days=expected_interval
        )
        assert result.next_review_date == expected_date

    def test_ease_factor_bounds(self):
        """Test that ease factor respects minimum and maximum bounds."""
        config = SpacedRepetitionConfig()

        # Test minimum bound
        result = calculate_next_review(
            Grade.WRONG,
            current_ease_factor=1.4,  # Close to minimum
            current_interval_days=1,
            current_repetitions=1,
            config=config,
        )
        assert result.ease_factor == 1.3  # Should hit minimum

        # Test maximum bound
        result = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.9,  # Close to maximum
            current_interval_days=1,
            current_repetitions=1,
            config=config,
        )
        assert result.ease_factor == 3.0  # Should hit maximum

    def test_interval_bounds(self):
        """Test that intervals respect minimum and maximum bounds."""
        config = SpacedRepetitionConfig(minimum_interval_days=2, maximum_interval_days=10)

        # Test minimum bound
        result = calculate_next_review(
            Grade.PARTIAL,
            current_ease_factor=2.5,
            current_interval_days=4,  # Half would be 2
            current_repetitions=1,
            config=config,
        )
        assert result.interval_days == 2  # Should hit minimum

        # Test maximum bound
        result = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.5,
            current_interval_days=8,
            current_repetitions=3,  # Would calculate to ~27
            config=config,
        )
        assert result.interval_days == 10  # Should hit maximum


class TestCardDueChecking:
    """Test card due date checking functions."""

    @freeze_time("2025-01-15 12:00:00")
    def test_is_card_due_none_date(self):
        """Test that cards with no review date are due."""
        assert is_card_due(None) is True

    @freeze_time("2025-01-15 12:00:00")
    def test_is_card_due_past_date(self):
        """Test that cards with past review dates are due."""
        past_date = datetime(2025, 1, 14, 12, 0, 0)
        assert is_card_due(past_date) is True

    @freeze_time("2025-01-15 12:00:00")
    def test_is_card_due_current_time(self):
        """Test that cards due right now are due."""
        current_time = datetime(2025, 1, 15, 12, 0, 0)
        assert is_card_due(current_time) is True

    @freeze_time("2025-01-15 12:00:00")
    def test_is_card_due_future_date(self):
        """Test that cards with future review dates are not due."""
        future_date = datetime(2025, 1, 16, 12, 0, 0)
        assert is_card_due(future_date) is False

    def test_get_due_cards_count_empty_list(self):
        """Test due cards count with empty list."""
        assert get_due_cards_count([]) == 0

    @freeze_time("2025-01-15 12:00:00")
    def test_get_due_cards_count_mixed_reviews(self):
        """Test due cards count with mixed due/not due cards."""
        reviews = [
            {"next_review_date": None},  # Due (never reviewed)
            {"next_review_date": datetime(2025, 1, 14, 12, 0, 0)},  # Due (past)
            {"next_review_date": datetime(2025, 1, 15, 12, 0, 0)},  # Due (now)
            {"next_review_date": datetime(2025, 1, 16, 12, 0, 0)},  # Not due (future)
            {"next_review_date": datetime(2025, 1, 17, 12, 0, 0)},  # Not due (future)
        ]
        assert get_due_cards_count(reviews) == 3


class TestSpacedRepetitionWorkflow:
    """Test complete spaced repetition workflows."""

    @freeze_time("2025-01-15 12:00:00")
    def test_complete_learning_progression(self):
        """Test a complete learning progression for a card."""
        config = SpacedRepetitionConfig()

        # First review: Perfect
        result1 = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=0,
            config=config,
        )

        # Should be due tomorrow
        assert result1.interval_days == 1
        assert result1.repetitions == 1
        assert result1.ease_factor > 2.5  # Increased for perfect

        # Simulate time passing to next review
        with freeze_time("2025-01-16 12:00:00"):
            # Second review: Good
            result2 = calculate_next_review(
                Grade.GOOD,
                current_ease_factor=result1.ease_factor,
                current_interval_days=result1.interval_days,
                current_repetitions=result1.repetitions,
                config=config,
            )

            # Should use good_multiplier
            assert result2.repetitions == 2
            assert result2.interval_days == int(1 * 1.8)  # 1 day (minimum)

            # Simulate time passing to next review
            with freeze_time("2025-01-17 12:00:00"):
                # Third review: Perfect
                result3 = calculate_next_review(
                    Grade.PERFECT,
                    current_ease_factor=result2.ease_factor,
                    current_interval_days=result2.interval_days,
                    current_repetitions=result2.repetitions,
                    config=config,
                )

                # Should use ease factor with perfect bonus
                assert result3.repetitions == 3
                assert result3.interval_days > result2.interval_days
                assert result3.ease_factor > result2.ease_factor

    @freeze_time("2025-01-15 12:00:00")
    def test_learning_with_failures(self):
        """Test learning progression with wrong answers."""
        config = SpacedRepetitionConfig()

        # First review: Perfect
        result1 = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=0,
            config=config,
        )

        # Second review: Wrong (reset everything)
        result2 = calculate_next_review(
            Grade.WRONG,
            current_ease_factor=result1.ease_factor,
            current_interval_days=result1.interval_days,
            current_repetitions=result1.repetitions,
            config=config,
        )

        # Should reset repetitions and decrease ease factor
        assert result2.repetitions == 0
        assert result2.ease_factor < result1.ease_factor
        assert result2.interval_days == config.initial_interval_days

        # Third review: Good (starting over)
        result3 = calculate_next_review(
            Grade.GOOD,
            current_ease_factor=result2.ease_factor,
            current_interval_days=result2.interval_days,
            current_repetitions=result2.repetitions,
            config=config,
        )

        # Should increment repetitions again
        assert result3.repetitions == 1
        assert result3.interval_days == config.initial_interval_days

    def test_custom_configuration_impact(self):
        """Test that custom configuration affects calculations."""
        custom_config = SpacedRepetitionConfig(
            initial_interval_days=3,
            easy_multiplier=3.0,
            good_multiplier=2.2,
            minimum_interval_days=2,
            maximum_interval_days=30,
        )

        # Test with custom config
        result = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.5,
            current_interval_days=5,
            current_repetitions=2,
            config=custom_config,
        )

        # Should use custom multipliers and bounds
        # Ease factor increases to 2.65, then: 5 * 2.65 * 3.0 / 2.2 = ~18
        expected_interval = min(
            int(5 * 2.65 * 3.0 / 2.2),  # Custom multipliers with increased ease factor
            custom_config.maximum_interval_days,
        )
        expected_interval = max(expected_interval, custom_config.minimum_interval_days)

        assert result.interval_days == expected_interval


class TestSpacedRepetitionEdgeCases:
    """Test edge cases and error conditions."""

    def test_calculate_next_review_without_config(self):
        """Test that function works with default config when none provided."""
        result = calculate_next_review(
            Grade.GOOD,
            current_ease_factor=2.5,
            current_interval_days=1,
            current_repetitions=0,
            config=None,  # Should use default
        )

        assert result.repetitions == 1
        assert result.ease_factor == 2.5
        assert result.interval_days == 1

    @freeze_time("2025-01-15 12:00:00")
    def test_very_large_intervals(self):
        """Test that very large intervals are handled correctly."""
        config = SpacedRepetitionConfig(maximum_interval_days=365)

        result = calculate_next_review(
            Grade.PERFECT,
            current_ease_factor=2.5,
            current_interval_days=200,  # Very large
            current_repetitions=5,
            config=config,
        )

        # Should be capped at maximum
        assert result.interval_days <= config.maximum_interval_days
        expected_date = datetime(2025, 1, 15, 12, 0, 0) + timedelta(
            days=result.interval_days
        )
        assert result.next_review_date == expected_date

    def test_zero_interval_handling(self):
        """Test handling of zero or negative intervals."""
        config = SpacedRepetitionConfig()

        result = calculate_next_review(
            Grade.PARTIAL,
            current_ease_factor=2.5,
            current_interval_days=1,  # Half would be 0.5
            current_repetitions=1,
            config=config,
        )

        # Should respect minimum interval
        assert result.interval_days >= config.minimum_interval_days
