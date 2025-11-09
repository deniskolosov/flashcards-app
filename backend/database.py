"""
Database DAOs (Data Access Objects) for managing database operations.
"""

from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from backend.models import Base, ConfigModel, DeckModel, FlashcardModel, ReviewModel
from backend.schemas import (
    Deck,
    DeckCreate,
    DeckStats,
    DeckUpdate,
    Flashcard,
    FlashcardCreate,
    Review,
    ReviewCreate,
)
from backend.spaced_repetition import is_card_due


class Database:
    """Database connection manager for PostgreSQL."""

    def __init__(
        self,
        database_url: str = "postgresql://flashcards:flashcards_password@localhost:5432/flashcards_dev",
    ):
        self.database_url = database_url
        self.engine = self._create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.create_tables()

    def _create_engine(self, database_url: str) -> Engine:
        """Create PostgreSQL database engine with connection pooling."""
        # PostgreSQL configuration with connection pooling
        engine_kwargs = {
            "echo": False,
            "future": True,  # Use SQLAlchemy 2.0 style
            "poolclass": QueuePool,
            "pool_size": 10,  # Number of connections to maintain
            "max_overflow": 20,  # Additional connections beyond pool_size
            "pool_timeout": 30,  # Timeout when getting connection from pool
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_pre_ping": True,  # Validate connections before use
            "connect_args": {
                "connect_timeout": 10,  # Connection timeout
                "application_name": "flashcard-study-app",  # App identification
            },
        }

        return create_engine(database_url, **engine_kwargs)

    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def test_connection(self) -> bool:
        """Test PostgreSQL database connection."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception:
            return False

    def get_db_info(self) -> dict:
        """Get database information."""
        parsed_url = urlparse(self.database_url)
        return {
            "database_type": parsed_url.scheme,
            "host": parsed_url.hostname or "local",
            "database": parsed_url.path.lstrip("/") or "study_cards",
            "pool_size": getattr(self.engine.pool, "size", None),
            "connection_status": "connected" if self.test_connection() else "disconnected",
        }


class DeckDAO:
    """Data Access Object for Deck operations."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, deck_data: DeckCreate) -> Deck:
        """Create a new deck."""
        with self.db.get_session() as session:
            deck_model = DeckModel(name=deck_data.name, source_file=deck_data.source_file)
            session.add(deck_model)
            session.commit()
            session.refresh(deck_model)
            return Deck.model_validate(deck_model)

    def get_by_id(self, deck_id: str) -> Deck | None:
        """Get a deck by ID."""
        with self.db.get_session() as session:
            deck_model = session.query(DeckModel).filter(DeckModel.id == deck_id).first()
            if deck_model:
                return Deck.model_validate(deck_model)
            return None

    def get_all(self) -> list[Deck]:
        """Get all decks."""
        with self.db.get_session() as session:
            deck_models = session.query(DeckModel).all()
            return [Deck.model_validate(deck) for deck in deck_models]

    def update_last_studied(self, deck_id: str) -> None:
        """Update the last studied timestamp for a deck."""
        with self.db.get_session() as session:
            deck_model = session.query(DeckModel).filter(DeckModel.id == deck_id).first()
            if deck_model:
                deck_model.last_studied = datetime.now()
                session.commit()

    def update(self, deck_id: str, deck_data: DeckUpdate) -> Deck | None:
        """Update a deck's properties."""
        with self.db.get_session() as session:
            deck_model = session.query(DeckModel).filter(DeckModel.id == deck_id).first()
            if not deck_model:
                return None

            # Update fields if provided in deck_data
            if deck_data.name is not None:
                deck_model.name = deck_data.name
            if deck_data.source_file is not None:
                deck_model.source_file = deck_data.source_file

            session.commit()
            session.refresh(deck_model)
            return Deck.model_validate(deck_model)

    def delete(self, deck_id: str) -> bool:
        """Delete a deck and all its flashcards."""
        with self.db.get_session() as session:
            deck_model = session.query(DeckModel).filter(DeckModel.id == deck_id).first()
            if deck_model:
                session.delete(deck_model)
                session.commit()
                return True
            return False

    def bulk_delete(self, deck_ids: list[str]) -> dict[str, int]:
        """Delete multiple decks and all their flashcards."""
        with self.db.get_session() as session:
            deck_models = session.query(DeckModel).filter(DeckModel.id.in_(deck_ids)).all()

            deleted_count = len(deck_models)

            for deck_model in deck_models:
                session.delete(deck_model)

            session.commit()

            return {"deleted_count": deleted_count, "requested_count": len(deck_ids)}


class FlashcardDAO:
    """Data Access Object for Flashcard operations."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, deck_id: str, flashcard_data: FlashcardCreate) -> Flashcard:
        """Create a new flashcard."""
        with self.db.get_session() as session:
            flashcard_model = FlashcardModel(
                deck_id=deck_id, question=flashcard_data.question, answer=flashcard_data.answer
            )
            session.add(flashcard_model)
            session.commit()
            session.refresh(flashcard_model)
            return Flashcard.model_validate(flashcard_model)

    def get_by_id(self, flashcard_id: str) -> Flashcard | None:
        """Get a flashcard by ID."""
        with self.db.get_session() as session:
            flashcard_model = (
                session.query(FlashcardModel).filter(FlashcardModel.id == flashcard_id).first()
            )
            if flashcard_model:
                return Flashcard.model_validate(flashcard_model)
            return None

    def get_by_deck(self, deck_id: str) -> list[Flashcard]:
        """Get all flashcards for a deck."""
        with self.db.get_session() as session:
            flashcard_models = (
                session.query(FlashcardModel).filter(FlashcardModel.deck_id == deck_id).all()
            )
            return [Flashcard.model_validate(fc) for fc in flashcard_models]

    def delete(self, flashcard_id: str) -> bool:
        """Delete a flashcard."""
        with self.db.get_session() as session:
            flashcard_model = (
                session.query(FlashcardModel).filter(FlashcardModel.id == flashcard_id).first()
            )
            if flashcard_model:
                session.delete(flashcard_model)
                session.commit()
                return True
            return False


class ReviewDAO:
    """Data Access Object for Review operations."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, review_data: ReviewCreate) -> Review:
        """Create a new review."""
        with self.db.get_session() as session:
            review_model = ReviewModel(
                flashcard_id=review_data.flashcard_id,
                user_answer=review_data.user_answer,
                ai_score=review_data.ai_score,
                ai_grade=review_data.ai_grade,
                ai_feedback=review_data.ai_feedback,
                next_review_date=review_data.next_review_date,
                ease_factor=review_data.ease_factor,
                interval_days=review_data.interval_days,
                repetitions=review_data.repetitions,
            )
            session.add(review_model)
            session.commit()
            session.refresh(review_model)
            return Review.model_validate(review_model)

    def get_by_flashcard(self, flashcard_id: str) -> list[Review]:
        """Get all reviews for a flashcard."""
        with self.db.get_session() as session:
            review_models = (
                session.query(ReviewModel)
                .filter(ReviewModel.flashcard_id == flashcard_id)
                .order_by(ReviewModel.reviewed_at.desc())
                .all()
            )
            return [Review.model_validate(review) for review in review_models]

    def get_deck_stats(self, deck_id: str) -> DeckStats:
        """Get statistics for a deck."""
        with self.db.get_session() as session:
            # Get all flashcards for the deck
            flashcard_models = (
                session.query(FlashcardModel).filter(FlashcardModel.deck_id == deck_id).all()
            )
            total_cards = len(flashcard_models)

            if total_cards == 0:
                return DeckStats(
                    total_cards=0,
                    reviewed_cards=0,
                    average_score=0.0,
                    perfect_count=0,
                    good_count=0,
                    partial_count=0,
                    wrong_count=0,
                )

            # Get all reviews for these flashcards
            flashcard_ids = [fc.id for fc in flashcard_models]
            reviews = (
                session.query(ReviewModel).filter(ReviewModel.flashcard_id.in_(flashcard_ids)).all()
            )

            if not reviews:
                # Still calculate due cards count even if no reviews exist
                due_cards = self.get_due_cards_count(deck_id)
                return DeckStats(
                    total_cards=total_cards,
                    reviewed_cards=0,
                    average_score=0.0,
                    perfect_count=0,
                    good_count=0,
                    partial_count=0,
                    wrong_count=0,
                    due_cards=due_cards,
                )

            # Calculate statistics
            reviewed_card_ids = {review.flashcard_id for review in reviews}
            reviewed_cards = len(reviewed_card_ids)

            total_score = sum(review.ai_score for review in reviews)
            average_score = total_score / len(reviews)

            grade_counts = {
                "Perfect": sum(1 for r in reviews if r.ai_grade == "Perfect"),
                "Good": sum(1 for r in reviews if r.ai_grade == "Good"),
                "Partial": sum(1 for r in reviews if r.ai_grade == "Partial"),
                "Wrong": sum(1 for r in reviews if r.ai_grade == "Wrong"),
            }

            # Calculate due cards count
            due_cards = self.get_due_cards_count(deck_id)

            return DeckStats(
                total_cards=total_cards,
                reviewed_cards=reviewed_cards,
                average_score=round(average_score, 2),
                perfect_count=grade_counts["Perfect"],
                good_count=grade_counts["Good"],
                partial_count=grade_counts["Partial"],
                wrong_count=grade_counts["Wrong"],
                due_cards=due_cards,
            )

    def get_latest_reviews_by_deck(self, deck_id: str) -> list[Review]:
        """Get the latest review for each flashcard in a deck."""
        with self.db.get_session() as session:
            # Get all flashcards for the deck
            flashcard_models = (
                session.query(FlashcardModel).filter(FlashcardModel.deck_id == deck_id).all()
            )

            if not flashcard_models:
                return []

            flashcard_ids = [fc.id for fc in flashcard_models]
            latest_reviews = []

            # Get the latest review for each flashcard
            for flashcard_id in flashcard_ids:
                latest_review = (
                    session.query(ReviewModel)
                    .filter(ReviewModel.flashcard_id == flashcard_id)
                    .order_by(ReviewModel.reviewed_at.desc())
                    .first()
                )

                if latest_review:
                    latest_reviews.append(Review.model_validate(latest_review))

            return latest_reviews

    def get_due_cards_count(self, deck_id: str) -> int:
        """Get count of cards due for review in a deck."""
        with self.db.get_session() as session:
            # Get all flashcards for the deck
            flashcard_models = (
                session.query(FlashcardModel).filter(FlashcardModel.deck_id == deck_id).all()
            )

            if not flashcard_models:
                return 0

            due_count = 0
            flashcard_ids = [fc.id for fc in flashcard_models]

            for flashcard_id in flashcard_ids:
                # Get latest review for this flashcard
                latest_review = (
                    session.query(ReviewModel)
                    .filter(ReviewModel.flashcard_id == flashcard_id)
                    .order_by(ReviewModel.reviewed_at.desc())
                    .first()
                )

                # Check if card is due
                if latest_review is None:
                    # Never reviewed, so it's due
                    due_count += 1
                elif is_card_due(latest_review.next_review_date):
                    due_count += 1

            return due_count

    def get_due_flashcards(self, deck_id: str) -> list[Flashcard]:
        """Get flashcards that are due for review in a deck."""
        with self.db.get_session() as session:
            # Get all flashcards for the deck
            flashcard_models = (
                session.query(FlashcardModel).filter(FlashcardModel.deck_id == deck_id).all()
            )

            if not flashcard_models:
                return []

            due_flashcards = []

            for flashcard_model in flashcard_models:
                # Get latest review for this flashcard
                latest_review = (
                    session.query(ReviewModel)
                    .filter(ReviewModel.flashcard_id == flashcard_model.id)
                    .order_by(ReviewModel.reviewed_at.desc())
                    .first()
                )

                # Check if card is due
                if latest_review is None:
                    # Never reviewed, so it's due
                    due_flashcards.append(Flashcard.model_validate(flashcard_model))
                elif is_card_due(latest_review.next_review_date):
                    due_flashcards.append(Flashcard.model_validate(flashcard_model))

            return due_flashcards


class ConfigDAO:
    """Data Access Object for Config operations."""

    def __init__(self, db: Database):
        self.db = db

    def set(self, key: str, value: str) -> None:
        """Set a configuration value."""
        with self.db.get_session() as session:
            config_model = session.query(ConfigModel).filter(ConfigModel.key == key).first()
            if config_model:
                config_model.value = value
            else:
                config_model = ConfigModel(key=key, value=value)
                session.add(config_model)
            session.commit()

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a configuration value."""
        with self.db.get_session() as session:
            config_model = session.query(ConfigModel).filter(ConfigModel.key == key).first()
            return config_model.value if config_model else default

    def get_all(self) -> dict:
        """Get all configuration values."""
        with self.db.get_session() as session:
            configs = session.query(ConfigModel).all()
            return {config.key: config.value for config in configs}
