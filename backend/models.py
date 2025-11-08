"""
SQLAlchemy ORM models for database tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DeckModel(Base):
    """SQLAlchemy model for decks table."""

    __tablename__ = "decks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_file: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())
    last_studied: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    flashcards: Mapped[list["FlashcardModel"]] = relationship(
        "FlashcardModel", back_populates="deck", cascade="all, delete-orphan"
    )


class FlashcardModel(Base):
    """SQLAlchemy model for flashcards table."""

    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id: Mapped[str] = mapped_column(String, ForeignKey("decks.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())

    # Relationships
    deck: Mapped["DeckModel"] = relationship("DeckModel", back_populates="flashcards")
    reviews: Mapped[list["ReviewModel"]] = relationship(
        "ReviewModel", back_populates="flashcard", cascade="all, delete-orphan"
    )


class ReviewModel(Base):
    """SQLAlchemy model for reviews table."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    flashcard_id: Mapped[str] = mapped_column(String, ForeignKey("flashcards.id"), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    ai_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    ai_grade: Mapped[str] = mapped_column(String, nullable=False)  # Perfect/Good/Partial/Wrong
    ai_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Spaced Repetition fields (SM-2 Modified algorithm)
    ease_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.5
    )  # SM-2 ease factor
    interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # Days until next review
    repetitions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Number of successful reviews

    # Relationships
    flashcard: Mapped["FlashcardModel"] = relationship("FlashcardModel", back_populates="reviews")


class ConfigModel(Base):
    """SQLAlchemy model for config table."""

    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
