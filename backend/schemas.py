"""
Pydantic schemas (DTOs) for API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Flashcard schemas
class FlashcardBase(BaseModel):
    """Base flashcard schema."""

    question: str = Field(..., min_length=1, description="The question text")
    answer: str = Field(..., min_length=1, description="The reference answer text")


class FlashcardCreate(FlashcardBase):
    """Schema for creating a flashcard."""

    pass


class Flashcard(FlashcardBase):
    """Schema for flashcard response."""

    id: str
    deck_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Deck schemas
class DeckBase(BaseModel):
    """Base deck schema."""

    name: str = Field(..., min_length=1, description="Deck name")


class DeckCreate(DeckBase):
    """Schema for creating a deck."""

    source_file: str | None = None


class DeckUpdate(BaseModel):
    """Schema for updating a deck."""

    name: str | None = Field(None, min_length=1, description="Updated deck name")
    source_file: str | None = Field(None, description="Updated source file path")


class Deck(DeckBase):
    """Schema for deck response."""

    id: str
    source_file: str | None = None
    created_at: datetime
    last_studied: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DeckWithStats(Deck):
    """Deck with statistics."""

    total_cards: int = 0
    reviewed_cards: int = 0
    average_score: float = 0.0
    due_cards: int = 0  # Number of cards due for review


class DeckImportRequest(BaseModel):
    """Request to import a deck from markdown file."""

    file_path: str = Field(..., description="Path to markdown file")
    deck_name: str | None = Field(None, description="Optional deck name (defaults to filename)")


class DeckBulkDeleteRequest(BaseModel):
    """Request to bulk delete multiple decks."""

    deck_ids: list[str] = Field(..., min_length=1, description="List of deck IDs to delete")


# Review/Grading schemas
class GradeRequest(BaseModel):
    """Request to grade a user's answer."""

    flashcard_id: str = Field(..., description="ID of the flashcard being answered")
    user_answer: str = Field(..., min_length=1, description="User's answer to grade")


class GradingResult(BaseModel):
    """Result from AI grading."""

    score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    grade: str = Field(..., description="Grade: Perfect/Good/Partial/Wrong")
    feedback: str = Field(..., description="Detailed feedback from AI")
    key_concepts_covered: list[str] | None = Field(
        default=None, description="Concepts the user covered"
    )
    key_concepts_missed: list[str] | None = Field(
        default=None, description="Concepts the user missed"
    )


class Review(BaseModel):
    """Schema for review response."""

    id: str
    flashcard_id: str
    reviewed_at: datetime
    user_answer: str
    ai_score: int
    ai_grade: str
    ai_feedback: str
    next_review_date: datetime | None = None

    # Spaced Repetition fields
    ease_factor: float = 2.5
    interval_days: int = 1
    repetitions: int = 0

    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    """Schema for creating a review."""

    flashcard_id: str
    user_answer: str
    ai_score: int
    ai_grade: str
    ai_feedback: str
    next_review_date: datetime | None = None

    # Spaced Repetition fields
    ease_factor: float = 2.5
    interval_days: int = 1
    repetitions: int = 0


# Statistics schemas
class DeckStats(BaseModel):
    """Statistics for a deck."""

    total_cards: int
    reviewed_cards: int
    average_score: float
    perfect_count: int
    good_count: int
    partial_count: int
    wrong_count: int
    due_cards: int = 0


class SessionStats(BaseModel):
    """Statistics for current session."""

    cards_reviewed: int
    average_score: float
    perfect_count: int
    good_count: int
    partial_count: int
    wrong_count: int
    duration_minutes: int | None = None


# Config schemas
class ConfigUpdate(BaseModel):
    """Update configuration."""

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    default_provider: str | None = Field(None, pattern="^(anthropic|openai)$")
    anthropic_model: str | None = None
    openai_model: str | None = None
    whisper_model: str | None = None

    # Spaced Repetition configuration
    initial_interval_days: int | None = Field(
        None, ge=1, le=365, description="Initial interval for new cards (days)"
    )
    easy_multiplier: float | None = Field(
        None, ge=1.0, le=5.0, description="Multiplier for Perfect grade"
    )
    good_multiplier: float | None = Field(
        None, ge=1.0, le=5.0, description="Multiplier for Good grade"
    )
    minimum_interval_days: int | None = Field(
        None, ge=1, le=30, description="Minimum interval between reviews (days)"
    )
    maximum_interval_days: int | None = Field(
        None, ge=30, le=3650, description="Maximum interval between reviews (days)"
    )


class ConfigResponse(BaseModel):
    """Configuration response (without API keys)."""

    default_provider: str
    anthropic_model: str
    openai_model: str
    whisper_model: str
    has_anthropic_key: bool
    has_openai_key: bool

    # Spaced Repetition configuration
    initial_interval_days: int = 1
    easy_multiplier: float = 2.5
    good_multiplier: float = 1.8
    minimum_interval_days: int = 1
    maximum_interval_days: int = 180


# Study session schemas
class StudySessionStart(BaseModel):
    """Start a study session."""

    deck_id: str
    card_limit: int | None = Field(None, ge=1, description="Max number of cards to study")


class StudySessionCard(BaseModel):
    """A card in a study session."""

    flashcard: Flashcard
    card_number: int
    total_cards: int


# Audio transcription schemas
class TranscriptionResponse(BaseModel):
    """Response from audio transcription."""

    text: str = Field(..., description="Transcribed text from audio")
    confidence: float | None = Field(None, description="Confidence score (0-1) if available")
