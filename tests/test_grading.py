"""
Tests for the AI grading service.
"""

import json
from unittest.mock import Mock, patch

import pytest
from anthropic.types import TextBlock
from pydantic import ValidationError

from backend.grading import GradingService
from backend.schemas import GradingResult


@pytest.fixture
def mock_anthropic_response():
    """Mock response from Anthropic API."""
    return {
        "score": 85,
        "grade": "Good",
        "feedback": "You covered the main concepts well. You missed mentioning X.",
        "key_concepts_covered": ["concept1", "concept2"],
        "key_concepts_missed": ["concept3"],
    }


@pytest.fixture
def mock_openai_response():
    """Mock response from OpenAI API."""
    return {
        "score": 90,
        "grade": "Perfect",
        "feedback": "Excellent answer! You covered all key points.",
        "key_concepts_covered": ["concept1", "concept2", "concept3"],
        "key_concepts_missed": [],
    }


def test_grading_service_initialization():
    """Test initializing the grading service."""
    service = GradingService(
        anthropic_api_key="test_anthropic_key",
        openai_api_key="test_openai_key",
        default_provider="anthropic",
    )

    assert service.anthropic_api_key == "test_anthropic_key"
    assert service.openai_api_key == "test_openai_key"
    assert service.default_provider == "anthropic"


def test_grade_with_anthropic(mock_anthropic_response):
    """Test grading with Anthropic API."""
    service = GradingService(anthropic_api_key="test_key", default_provider="anthropic")

    # Mock the Anthropic client
    with patch.object(service, "anthropic_client") as mock_client:
        mock_response = Mock()
        # Create a proper TextBlock instance for the content
        text_block = TextBlock(
            text=f"```json\n{str(mock_anthropic_response).replace("'", '"')}\n```", type="text"
        )
        mock_response.content = [text_block]
        mock_client.messages.create.return_value = mock_response

        result = service.grade_answer(
            question="What is Python?",
            reference_answer="Python is a programming language.",
            user_answer="Python is a language for programming.",
        )

        assert isinstance(result, GradingResult)
        assert result.score == 85
        assert result.grade == "Good"
        assert "covered the main concepts" in result.feedback


def test_grade_with_openai(mock_openai_response):
    """Test grading with OpenAI API."""
    service = GradingService(openai_api_key="test_key", default_provider="openai")

    # Mock the OpenAI client
    with patch.object(service, "openai_client") as mock_client:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps(mock_openai_response)))]
        mock_client.chat.completions.create.return_value = mock_response

        result = service.grade_answer(
            question="What is Python?",
            reference_answer="Python is a programming language.",
            user_answer="Python is a programming language.",
            provider="openai",
        )

        assert isinstance(result, GradingResult)
        assert result.score == 90
        assert result.grade == "Perfect"


def test_grade_without_api_key():
    """Test grading without API key raises error."""
    service = GradingService(default_provider="anthropic")

    with pytest.raises(ValueError, match="Anthropic API key not configured"):
        service.grade_answer(
            question="What is Python?",
            reference_answer="Python is a programming language.",
            user_answer="Python is a language.",
        )


def test_grade_with_invalid_provider():
    """Test grading with invalid provider raises error."""
    service = GradingService(anthropic_api_key="test_key")

    with pytest.raises(ValueError, match="Unknown provider"):
        service.grade_answer(
            question="What is Python?",
            reference_answer="Python is a programming language.",
            user_answer="Python is a language.",
            provider="invalid_provider",
        )


def test_extract_json_from_plain_text():
    """Test extracting JSON from plain text response."""
    service = GradingService(anthropic_api_key="test_key")

    json_text = '{"score": 85, "grade": "Good", "feedback": "Nice job"}'
    result = service._extract_json(json_text)

    assert result["score"] == 85
    assert result["grade"] == "Good"


def test_extract_json_from_code_block():
    """Test extracting JSON from markdown code block."""
    service = GradingService(anthropic_api_key="test_key")

    text_with_code_block = """
Here is the result:

```json
{
  "score": 90,
  "grade": "Perfect",
  "feedback": "Excellent work!"
}
```
"""
    result = service._extract_json(text_with_code_block)

    assert result["score"] == 90
    assert result["grade"] == "Perfect"


def test_extract_json_from_mixed_text():
    """Test extracting JSON from text with other content."""
    service = GradingService(anthropic_api_key="test_key")

    mixed_text = """
Some preamble text here.

{"score": 75, "grade": "Good", "feedback": "Could be better"}

Some text after the JSON.
"""
    result = service._extract_json(mixed_text)

    assert result["score"] == 75
    assert result["grade"] == "Good"


def test_extract_json_invalid_text():
    """Test that invalid JSON raises an error."""
    service = GradingService(anthropic_api_key="test_key")

    with pytest.raises(ValueError, match="Could not extract valid JSON"):
        service._extract_json("This is not JSON at all")


def test_test_connection_success():
    """Test the connection test with successful response."""
    service = GradingService(anthropic_api_key="test_key", default_provider="anthropic")

    with patch.object(service, "grade_answer") as mock_grade:
        mock_grade.return_value = GradingResult(
            score=100, grade="Perfect", feedback="Test successful"
        )

        success, message = service.test_connection()

        assert success is True
        assert "Anthropic" in message
        assert "successful" in message


def test_test_connection_failure():
    """Test the connection test with failed response."""
    service = GradingService(anthropic_api_key="test_key", default_provider="anthropic")

    with patch.object(service, "grade_answer") as mock_grade:
        mock_grade.side_effect = Exception("API connection failed")

        success, message = service.test_connection()

        assert success is False
        assert "error" in message.lower()


def test_grading_result_validation():
    """Test that GradingResult validates correctly."""
    # Valid result
    result = GradingResult(
        score=85,
        grade="Good",
        feedback="Well done!",
        key_concepts_covered=["concept1"],
        key_concepts_missed=["concept2"],
    )

    assert result.score == 85
    assert result.grade == "Good"

    # Invalid score (out of range) - Pydantic will raise ValidationError
    with pytest.raises(ValidationError):
        GradingResult(
            score=101,  # > 100
            grade="Good",
            feedback="Test",
        )

    with pytest.raises(ValidationError):
        GradingResult(
            score=-1,  # < 0
            grade="Good",
            feedback="Test",
        )


def test_grade_with_provider_override():
    """Test that provider override works."""
    service = GradingService(
        anthropic_api_key="anthropic_key", openai_api_key="openai_key", default_provider="anthropic"
    )

    mock_response = Mock()
    mock_response.choices = [
        Mock(
            message=Mock(content=json.dumps({"score": 95, "grade": "Perfect", "feedback": "Great"}))
        )
    ]

    with patch.object(service, "openai_client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response

        # Override to use OpenAI even though default is Anthropic
        result = service.grade_answer(
            question="Test",
            reference_answer="Test answer",
            user_answer="My answer",
            provider="openai",
        )

        # Should have called OpenAI, not Anthropic
        mock_client.chat.completions.create.assert_called_once()
        assert result.score == 95
