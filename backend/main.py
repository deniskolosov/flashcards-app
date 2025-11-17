"""
FastAPI main application for flashcard study app.
"""

import os
import uuid
from datetime import datetime

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import ConfigManager
from backend.database import ConfigDAO, Database, DeckDAO, FlashcardDAO, ReviewDAO
from backend.grading import GradingService
from backend.parser import parse_flashcard_content, parse_flashcard_file, validate_flashcard_file
from backend.schemas import (
    ConfigResponse,
    ConfigUpdate,
    Deck,
    DeckBulkDeleteRequest,
    DeckCreate,
    DeckImportRequest,
    DeckStats,
    DeckUpdate,
    Flashcard,
    FlashcardCreate,
    GradeRequest,
    GradingResult,
    ReviewCreate,
    StudySessionStart,
    TranscriptionResponse,
)
from backend.spaced_repetition import calculate_next_review, grade_from_ai_grade
from backend.whisper_service import WhisperService

# Initialize FastAPI app
app = FastAPI(
    title="Flashcard Study App",
    description="AI-powered flashcard study app with spaced repetition",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (will be replaced with dependency injection)
_db_instance: Database | None = None
_grading_service_instance: GradingService | None = None
_whisper_service_instance: WhisperService | None = None
_config_manager_instance: ConfigManager | None = None

# Study sessions storage (in-memory for now, could be moved to DB)
study_sessions: dict[str, dict] = {}


def get_db() -> Database:
    """Dependency to get database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def get_grading_service() -> GradingService:
    """Dependency to get grading service instance."""
    global _grading_service_instance
    if _grading_service_instance is None:
        config_manager = get_config_manager()
        _grading_service_instance = GradingService(
            anthropic_api_key=config_manager.get_api_key("anthropic"),
            openai_api_key=config_manager.get_api_key("openai"),
            default_provider=config_manager.get_default_provider(),
            anthropic_model=config_manager.get_model("anthropic"),
            openai_model=config_manager.get_model("openai"),
        )
    return _grading_service_instance


def get_whisper_service() -> WhisperService:
    """Dependency to get whisper service instance."""
    global _whisper_service_instance
    if _whisper_service_instance is None:
        config_manager = get_config_manager()
        _whisper_service_instance = WhisperService(
            openai_api_key=config_manager.get_api_key("openai"),
            model=config_manager.get_whisper_model(),
        )
    return _whisper_service_instance


def get_config_manager() -> ConfigManager:
    """Dependency to get config manager instance."""
    global _config_manager_instance
    if _config_manager_instance is None:
        db = get_db()
        config_dao = ConfigDAO(db)
        _config_manager_instance = ConfigManager(config_dao=config_dao)
    return _config_manager_instance


def refresh_grading_service():
    """Refresh grading service after config update."""
    global _grading_service_instance
    _grading_service_instance = None


def refresh_whisper_service():
    """Refresh whisper service after config update."""
    global _whisper_service_instance
    _whisper_service_instance = None


# Mount static files (frontend)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# Root endpoint - serve frontend
@app.get("/")
async def root():
    """Serve the frontend application."""
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not found. API is running at /docs"}


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Deck endpoints
@app.post("/api/decks", response_model=Deck)
async def create_deck(deck_data: DeckCreate, db: Database = Depends(get_db)):
    """Create a new deck."""
    deck_dao = DeckDAO(db)
    return deck_dao.create(deck_data)


@app.get("/api/decks")
async def get_all_decks(include_empty: bool = False, db: Database = Depends(get_db)):
    """Get all decks with statistics. By default, empty decks are filtered out."""
    deck_dao = DeckDAO(db)
    review_dao = ReviewDAO(db)

    decks = deck_dao.get_all()

    # Enrich each deck with stats
    decks_with_stats = []
    for deck in decks:
        deck_dict = deck.model_dump()
        stats = review_dao.get_deck_stats(deck.id)
        deck_dict["stats"] = stats.model_dump()

        # Filter out empty decks unless explicitly requested
        if include_empty or stats.total_cards > 0:
            decks_with_stats.append(deck_dict)

    return decks_with_stats


@app.get("/api/decks/{deck_id}", response_model=Deck)
async def get_deck(deck_id: str, db: Database = Depends(get_db)):
    """Get a deck by ID."""
    deck_dao = DeckDAO(db)
    deck = deck_dao.get_by_id(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@app.put("/api/decks/{deck_id}", response_model=Deck)
async def update_deck(deck_id: str, deck_data: DeckUpdate, db: Database = Depends(get_db)):
    """Update a deck's properties."""
    deck_dao = DeckDAO(db)
    deck = deck_dao.update(deck_id, deck_data)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@app.delete("/api/decks/{deck_id}")
async def delete_deck(deck_id: str, db: Database = Depends(get_db)):
    """Delete a deck and all its flashcards."""
    deck_dao = DeckDAO(db)
    success = deck_dao.delete(deck_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deck not found")
    return {"message": "Deck deleted successfully"}


@app.post("/api/decks/bulk-delete")
async def bulk_delete_decks(request: DeckBulkDeleteRequest, db: Database = Depends(get_db)):
    """Delete multiple decks and all their flashcards."""
    deck_dao = DeckDAO(db)
    result = deck_dao.bulk_delete(request.deck_ids)

    if result["deleted_count"] == 0:
        raise HTTPException(status_code=404, detail="No decks found to delete")

    message = f"Successfully deleted {result['deleted_count']} deck(s)"
    if result["deleted_count"] < result["requested_count"]:
        message += f" ({result['requested_count'] - result['deleted_count']} deck(s) not found)"

    return {
        "message": message,
        "deleted_count": result["deleted_count"],
        "requested_count": result["requested_count"],
    }


@app.post("/api/decks/import")
async def import_deck(
    file: UploadFile = File(...), deck_name: str | None = Form(None), db: Database = Depends(get_db)
):
    """Import a deck from an uploaded markdown file."""
    # Validate file type
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="File must be a markdown (.md) file")

    # Read file content
    try:
        content = await file.read()
        content_str = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e!s}") from e

    # Parse flashcards from content
    try:
        flashcards = parse_flashcard_content(content_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse flashcards: {e!s}") from e

    if not flashcards:
        raise HTTPException(status_code=400, detail="No valid flashcards found in file")

    # Create deck
    deck_dao = DeckDAO(db)
    flashcard_dao = FlashcardDAO(db)

    final_deck_name = deck_name or file.filename.replace(".md", "")
    deck = deck_dao.create(DeckCreate(name=final_deck_name, source_file=file.filename))

    # Create flashcards
    for card_data in flashcards:
        flashcard_dao.create(
            deck.id, FlashcardCreate(question=card_data["question"], answer=card_data["answer"])
        )

    return {
        "deck": deck,
        "flashcards_count": len(flashcards),
        "message": f"Successfully imported {len(flashcards)} flashcards",
    }


@app.post("/api/decks/import-from-path")
async def import_deck_from_path(import_request: DeckImportRequest, db: Database = Depends(get_db)):
    """Import a deck from a markdown file path (for local files)."""
    # Validate file
    is_valid, message = validate_flashcard_file(import_request.file_path)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # Parse flashcards
    flashcards = parse_flashcard_file(import_request.file_path)

    # Create deck
    deck_dao = DeckDAO(db)
    flashcard_dao = FlashcardDAO(db)

    deck_name = import_request.deck_name or import_request.file_path.split("/")[-1].replace(
        ".md", ""
    )
    deck = deck_dao.create(DeckCreate(name=deck_name, source_file=import_request.file_path))

    # Create flashcards
    for card_data in flashcards:
        flashcard_dao.create(
            deck.id, FlashcardCreate(question=card_data["question"], answer=card_data["answer"])
        )

    return {
        "deck": deck,
        "flashcards_count": len(flashcards),
        "message": f"Successfully imported {len(flashcards)} flashcards",
    }


# Flashcard endpoints
@app.get("/api/decks/{deck_id}/flashcards", response_model=list[Flashcard])
async def get_flashcards(deck_id: str, db: Database = Depends(get_db)):
    """Get all flashcards for a deck."""
    # Verify deck exists
    deck_dao = DeckDAO(db)
    if not deck_dao.get_by_id(deck_id):
        raise HTTPException(status_code=404, detail="Deck not found")

    flashcard_dao = FlashcardDAO(db)
    return flashcard_dao.get_by_deck(deck_id)


@app.post("/api/decks/{deck_id}/flashcards", response_model=Flashcard)
async def create_flashcard(
    deck_id: str, flashcard_data: FlashcardCreate, db: Database = Depends(get_db)
):
    """Create a flashcard in a deck."""
    # Verify deck exists
    deck_dao = DeckDAO(db)
    if not deck_dao.get_by_id(deck_id):
        raise HTTPException(status_code=404, detail="Deck not found")

    flashcard_dao = FlashcardDAO(db)
    return flashcard_dao.create(deck_id, flashcard_data)


# Due cards endpoints
@app.get("/api/decks/{deck_id}/due-cards", response_model=list[Flashcard])
async def get_due_cards(deck_id: str, db: Database = Depends(get_db)):
    """Get flashcards that are due for review in a deck."""
    # Verify deck exists
    deck_dao = DeckDAO(db)
    if not deck_dao.get_by_id(deck_id):
        raise HTTPException(status_code=404, detail="Deck not found")

    review_dao = ReviewDAO(db)
    return review_dao.get_due_flashcards(deck_id)


# Study session endpoints
@app.post("/api/sessions/start-due", response_model=dict)
async def start_due_study_session(session_data: StudySessionStart, db: Database = Depends(get_db)):
    """Start a study session with only due cards."""
    global study_sessions

    # Get due cards for the deck
    review_dao = ReviewDAO(db)
    due_cards = review_dao.get_due_flashcards(session_data.deck_id)

    if not due_cards:
        raise HTTPException(status_code=404, detail="No cards are due for review in this deck")

    # Apply card limit if specified
    cards_to_study = due_cards
    if session_data.card_limit:
        cards_to_study = due_cards[: session_data.card_limit]

    # Create session (use same structure as regular sessions)
    session_id = str(uuid.uuid4())
    study_sessions[session_id] = {
        "deck_id": session_data.deck_id,
        "flashcards": [card.id for card in cards_to_study],  # Store IDs like regular sessions
        "current_index": 0,
        "total_cards": len(cards_to_study),
        "started_at": datetime.now(),
        "type": "due_only",  # Mark this as a due-only session
    }

    return {
        "session_id": session_id,
        "total_due_cards": len(due_cards),
        "cards_in_session": len(cards_to_study),
        "message": f"Started due cards study session with {len(cards_to_study)} cards",
    }


# Grading endpoint
@app.post("/api/grade", response_model=GradingResult)
async def grade_answer(
    grade_request: GradeRequest,
    db: Database = Depends(get_db),
    grading_service: GradingService = Depends(get_grading_service),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """Grade a user's answer."""
    # Get flashcard
    flashcard_dao = FlashcardDAO(db)
    flashcard = flashcard_dao.get_by_id(grade_request.flashcard_id)
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    # Grade the answer
    try:
        result = grading_service.grade_answer(
            question=flashcard.question,
            reference_answer=flashcard.answer,
            user_answer=grade_request.user_answer,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grading error: {e!s}") from e

    # Get previous review data for spaced repetition
    review_dao = ReviewDAO(db)
    previous_reviews = review_dao.get_by_flashcard(flashcard.id)

    # Get spaced repetition values from most recent review, or use defaults for new card
    if previous_reviews:
        latest_review = max(previous_reviews, key=lambda r: r.reviewed_at)
        current_ease_factor = latest_review.ease_factor
        current_interval_days = latest_review.interval_days
        current_repetitions = latest_review.repetitions
    else:
        # New card defaults
        current_ease_factor = 2.5
        current_interval_days = 1
        current_repetitions = 0

    # Calculate spaced repetition values
    grade = grade_from_ai_grade(result.grade)
    config = config_manager.get_spaced_repetition_config()
    sr_result = calculate_next_review(
        grade=grade,
        current_ease_factor=current_ease_factor,
        current_interval_days=current_interval_days,
        current_repetitions=current_repetitions,
        config=config,
    )

    # Save review with spaced repetition data
    review_dao.create(
        ReviewCreate(
            flashcard_id=flashcard.id,
            user_answer=grade_request.user_answer,
            ai_score=result.score,
            ai_grade=result.grade,
            ai_feedback=result.feedback,
            next_review_date=sr_result.next_review_date,
            ease_factor=sr_result.ease_factor,
            interval_days=sr_result.interval_days,
            repetitions=sr_result.repetitions,
        )
    )

    # Update deck last studied
    deck_dao = DeckDAO(db)
    deck_dao.update_last_studied(flashcard.deck_id)

    return result


# Audio transcription endpoint
@app.post("/api/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    whisper_service: WhisperService = Depends(get_whisper_service),
):
    """Transcribe audio to text using OpenAI Whisper."""
    # Validate file type
    allowed_types = [
        "audio/wav",
        "audio/mp3",
        "audio/webm",
        "audio/ogg",
        "audio/m4a",
        "audio/mp4",
        "audio/x-wav",
        "audio/mpeg",
    ]

    if audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {audio.content_type}. "
            f"Supported formats: {', '.join(allowed_types)}",
        )

    # Check file size (limit to 25MB as per OpenAI Whisper API)
    max_size = 25 * 1024 * 1024  # 25MB
    audio_data = await audio.read()

    if len(audio_data) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Audio file too large. Maximum size is 25MB, got {len(audio_data) / 1024 / 1024:.1f}MB",
        )

    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        result = whisper_service.transcribe_audio(
            audio_data=audio_data, filename=audio.filename or "audio.webm"
        )
        return result
    except ValueError as e:
        # API key not configured
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        # Other transcription errors
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e!s}") from e


# Statistics endpoint
@app.get("/api/decks/{deck_id}/stats", response_model=DeckStats)
async def get_deck_stats(deck_id: str, db: Database = Depends(get_db)):
    """Get statistics for a deck."""
    # Verify deck exists
    deck_dao = DeckDAO(db)
    if not deck_dao.get_by_id(deck_id):
        raise HTTPException(status_code=404, detail="Deck not found")

    review_dao = ReviewDAO(db)
    return review_dao.get_deck_stats(deck_id)


# Configuration endpoints
@app.get("/api/config", response_model=ConfigResponse)
async def get_config(config_manager: ConfigManager = Depends(get_config_manager)):
    """Get configuration."""
    return config_manager.get_config_response()


@app.put("/api/config", response_model=ConfigResponse)
async def update_config(
    config_update: ConfigUpdate, config_manager: ConfigManager = Depends(get_config_manager)
):
    """Update configuration."""
    result = config_manager.update_config(config_update)
    # Refresh services with new config
    refresh_grading_service()
    refresh_whisper_service()
    return result


@app.post("/api/config/test")
async def test_ai_connection(
    request: dict, grading_service: GradingService = Depends(get_grading_service)
):
    """Test AI provider connection."""
    provider = request.get("provider")
    success, message = grading_service.test_connection(provider)
    return {"success": success, "message": message}


# Study session endpoints
@app.post("/api/sessions/start")
async def start_study_session(session_request: StudySessionStart, db: Database = Depends(get_db)):
    """Start a study session."""
    # Verify deck exists
    deck_dao = DeckDAO(db)
    deck = deck_dao.get_by_id(session_request.deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Get flashcards
    flashcard_dao = FlashcardDAO(db)
    flashcards = flashcard_dao.get_by_deck(session_request.deck_id)

    if not flashcards:
        raise HTTPException(status_code=400, detail="No flashcards in deck")

    # Apply card limit if specified
    if session_request.card_limit:
        flashcards = flashcards[: session_request.card_limit]

    # Create session
    session_id = str(uuid.uuid4())
    study_sessions[session_id] = {
        "deck_id": session_request.deck_id,
        "flashcards": [fc.id for fc in flashcards],
        "current_index": 0,
        "total_cards": len(flashcards),
    }

    return {
        "session_id": session_id,
        "deck_id": session_request.deck_id,
        "total_cards": len(flashcards),
    }


@app.get("/api/sessions/{session_id}/next")
async def get_next_card(session_id: str, db: Database = Depends(get_db)):
    """Get the next card in a study session."""
    if session_id not in study_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = study_sessions[session_id]
    current_index = session["current_index"]

    # Check if session is complete
    if current_index >= session["total_cards"]:
        return {"complete": True}

    # Get flashcard
    flashcard_id = session["flashcards"][current_index]
    flashcard_dao = FlashcardDAO(db)
    flashcard = flashcard_dao.get_by_id(flashcard_id)

    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    # Increment index for next call
    session["current_index"] += 1

    return {
        "complete": False,
        "flashcard": flashcard.model_dump(),
        "card_number": current_index + 1,
        "total_cards": session["total_cards"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
