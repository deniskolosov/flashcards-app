"""
SM-2 Modified spaced repetition algorithm implementation.

Based on the SuperMemo 2 algorithm with improvements:
- Configurable multipliers for different grades
- Better failure handling (reset ease factor on wrong answers)
- Minimum and maximum interval constraints
- Grade mapping: Perfect(4) -> Good(3) -> Partial(2) -> Wrong(1)
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import NamedTuple


class Grade(Enum):
    """Grade values for spaced repetition algorithm."""

    WRONG = 1  # Reset learning
    PARTIAL = 2  # Retry soon
    GOOD = 3  # Normal progression
    PERFECT = 4  # Accelerated progression


class SpacedRepetitionConfig(NamedTuple):
    """Configuration for spaced repetition algorithm."""

    initial_interval_days: int = 1  # Initial interval for new cards
    easy_multiplier: float = 2.5  # Multiplier for Perfect grade
    good_multiplier: float = 1.8  # Multiplier for Good grade
    minimum_interval_days: int = 1  # Minimum interval between reviews
    maximum_interval_days: int = 180  # Maximum interval between reviews
    ease_factor_minimum: float = 1.3  # Minimum ease factor
    ease_factor_maximum: float = 3.0  # Maximum ease factor
    ease_factor_decrease: float = 0.2  # Decrease for Partial grade
    ease_factor_increase: float = 0.15  # Increase for Perfect grade


class SpacedRepetitionResult(NamedTuple):
    """Result of spaced repetition calculation."""

    next_review_date: datetime
    ease_factor: float
    interval_days: int
    repetitions: int


def grade_from_ai_grade(ai_grade: str) -> Grade:
    """Convert AI grade string to Grade enum."""
    grade_mapping = {
        "Perfect": Grade.PERFECT,
        "Good": Grade.GOOD,
        "Partial": Grade.PARTIAL,
        "Wrong": Grade.WRONG,
    }
    return grade_mapping.get(ai_grade, Grade.WRONG)


def calculate_next_review(
    grade: Grade,
    current_ease_factor: float = 2.5,
    current_interval_days: int = 1,
    current_repetitions: int = 0,
    config: SpacedRepetitionConfig | None = None,
) -> SpacedRepetitionResult:
    """
    Calculate the next review date and update spaced repetition parameters.

    Args:
        grade: The grade received for this review
        current_ease_factor: Current ease factor for this card
        current_interval_days: Current interval in days
        current_repetitions: Number of successful repetitions so far
        config: Spaced repetition configuration

    Returns:
        SpacedRepetitionResult with updated values
    """
    if config is None:
        config = SpacedRepetitionConfig()

    # Start with current values
    ease_factor = current_ease_factor
    repetitions = current_repetitions

    # Handle different grades
    if grade == Grade.WRONG:
        # Reset on wrong answer
        repetitions = 0
        ease_factor = max(config.ease_factor_minimum, ease_factor - config.ease_factor_decrease)
        interval_days = config.initial_interval_days

    elif grade == Grade.PARTIAL:
        # Retry soon but don't reset completely
        repetitions = 0  # Reset repetition counter
        ease_factor = max(config.ease_factor_minimum, ease_factor - config.ease_factor_decrease)
        interval_days = max(1, current_interval_days // 2)  # Half the interval

    elif grade == Grade.GOOD:
        # Normal progression
        repetitions += 1
        if repetitions == 1:
            interval_days = config.initial_interval_days
        elif repetitions == 2:
            interval_days = int(config.initial_interval_days * config.good_multiplier)
        else:
            interval_days = int(current_interval_days * ease_factor)

    elif grade == Grade.PERFECT:
        # Accelerated progression
        repetitions += 1
        ease_factor = min(config.ease_factor_maximum, ease_factor + config.ease_factor_increase)

        if repetitions == 1:
            interval_days = config.initial_interval_days
        elif repetitions == 2:
            interval_days = int(config.initial_interval_days * config.easy_multiplier)
        else:
            interval_days = int(
                current_interval_days
                * ease_factor
                * config.easy_multiplier
                / config.good_multiplier
            )

    # Apply min/max constraints
    interval_days = max(config.minimum_interval_days, interval_days)
    interval_days = min(config.maximum_interval_days, interval_days)

    # Calculate next review date
    next_review_date = datetime.now() + timedelta(days=interval_days)

    return SpacedRepetitionResult(
        next_review_date=next_review_date,
        ease_factor=ease_factor,
        interval_days=interval_days,
        repetitions=repetitions,
    )


def is_card_due(next_review_date: datetime | None) -> bool:
    """
    Check if a card is due for review.

    Args:
        next_review_date: The scheduled next review date, or None if never reviewed

    Returns:
        True if the card is due for review
    """
    if next_review_date is None:
        return True  # New cards are always due

    current_time = datetime.now()

    # Handle timezone-naive datetimes from database
    if next_review_date.tzinfo is None:
        # Compare as timezone-naive datetimes
        pass
    else:
        # Remove timezone for comparison with naive datetime
        next_review_date = next_review_date.replace(tzinfo=None)

    return current_time >= next_review_date


def get_due_cards_count(reviews: list[dict]) -> int:
    """
    Count how many cards are due for review from a list of latest reviews.

    Args:
        reviews: List of review dictionaries with 'next_review_date' keys

    Returns:
        Number of cards due for review
    """
    due_count = 0
    for review in reviews:
        if is_card_due(review.get("next_review_date")):
            due_count += 1
    return due_count
