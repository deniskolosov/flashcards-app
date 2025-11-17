"""
Tests for the Whisper transcription service.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backend.schemas import TranscriptionResponse
from backend.whisper_service import WhisperService


@pytest.fixture
def mock_whisper_response():
    """Mock response from OpenAI Whisper API."""
    return "This is a test transcription of the audio content."


@pytest.fixture
def sample_audio_data():
    """Create sample audio data for testing."""
    # Create minimal WAV file data for testing
    sample_rate = 8000
    duration = 1  # 1 second
    num_samples = sample_rate * duration

    # WAV header
    header = bytearray()
    header.extend(b"RIFF")  # Chunk ID
    header.extend((36 + num_samples * 2).to_bytes(4, "little"))  # Chunk Size
    header.extend(b"WAVE")  # Format
    header.extend(b"fmt ")  # Subchunk1 ID
    header.extend((16).to_bytes(4, "little"))  # Subchunk1 Size
    header.extend((1).to_bytes(2, "little"))  # Audio Format (PCM)
    header.extend((1).to_bytes(2, "little"))  # Num Channels (mono)
    header.extend(sample_rate.to_bytes(4, "little"))  # Sample Rate
    header.extend((sample_rate * 2).to_bytes(4, "little"))  # Byte Rate
    header.extend((2).to_bytes(2, "little"))  # Block Align
    header.extend((16).to_bytes(2, "little"))  # Bits Per Sample
    header.extend(b"data")  # Subchunk2 ID
    header.extend((num_samples * 2).to_bytes(4, "little"))  # Subchunk2 Size

    # Silence data (all zeros)
    silence = bytes(num_samples * 2)

    return bytes(header) + silence


def test_whisper_service_initialization():
    """Test initializing the whisper service."""
    service = WhisperService(
        openai_api_key="test_openai_key",
        model="whisper-1",
    )

    assert service.openai_api_key == "test_openai_key"
    assert service.model == "whisper-1"
    assert service.client is not None


def test_whisper_service_initialization_without_key():
    """Test initializing the whisper service without API key."""
    service = WhisperService()

    assert service.openai_api_key is None
    assert service.model == "whisper-1"
    assert service.client is None


def test_transcribe_audio_success(mock_whisper_response, sample_audio_data):
    """Test successful audio transcription."""
    service = WhisperService(openai_api_key="test_key")

    # Mock the OpenAI client
    with patch.object(service, "client") as mock_client:
        mock_client.audio.transcriptions.create.return_value = mock_whisper_response

        result = service.transcribe_audio(audio_data=sample_audio_data, filename="test.wav")

        assert isinstance(result, TranscriptionResponse)
        assert (
            result.text == "This is a test transcription of the audio content"
        )  # Period removed by cleaning
        assert result.confidence is None

        # Verify the API call
        mock_client.audio.transcriptions.create.assert_called_once()
        call_args = mock_client.audio.transcriptions.create.call_args
        assert call_args[1]["model"] == "whisper-1"
        assert call_args[1]["response_format"] == "text"


def test_transcribe_audio_no_api_key():
    """Test transcription without API key configured."""
    service = WhisperService()

    with pytest.raises(ValueError, match="OpenAI API key not configured"):
        service.transcribe_audio(b"fake_audio_data", "test.wav")


def test_transcribe_audio_empty_data():
    """Test transcription with empty audio data."""
    service = WhisperService(openai_api_key="test_key")

    with pytest.raises(ValueError, match="No audio data provided"):
        service.transcribe_audio(b"", "test.wav")


def test_transcribe_audio_api_error(sample_audio_data):
    """Test handling of API errors during transcription."""
    service = WhisperService(openai_api_key="test_key")

    # Mock the OpenAI client to raise an exception
    with patch.object(service, "client") as mock_client:
        mock_client.audio.transcriptions.create.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="Error transcribing audio: API Error"):
            service.transcribe_audio(sample_audio_data, "test.wav")


def test_get_file_extension():
    """Test file extension detection."""
    service = WhisperService(openai_api_key="test_key")

    assert service._get_file_extension("audio.mp3") == ".mp3"
    assert service._get_file_extension("audio.wav") == ".wav"
    assert service._get_file_extension("audio.webm") == ".webm"
    assert service._get_file_extension("audio") == ".webm"  # default


def test_clean_transcription():
    """Test transcription text cleaning."""
    service = WhisperService(openai_api_key="test_key")

    # Test removing trailing period
    assert service._clean_transcription("Hello world.") == "Hello world"

    # Test normalizing whitespace
    assert service._clean_transcription("  Hello   world  ") == "Hello world"

    # Test empty text
    assert service._clean_transcription("") == ""
    assert service._clean_transcription("   ") == ""


def test_test_connection_success():
    """Test successful connection test."""
    service = WhisperService(openai_api_key="test_key")

    with patch.object(service, "client") as mock_client:
        mock_client.audio.transcriptions.create.return_value = "test"

        success, message = service.test_connection()

        assert success is True
        assert "successful" in message.lower()


def test_test_connection_no_api_key():
    """Test connection test without API key."""
    service = WhisperService()

    success, message = service.test_connection()

    assert success is False
    assert "not configured" in message.lower()


def test_test_connection_api_error():
    """Test connection test with API error."""
    service = WhisperService(openai_api_key="test_key")

    with patch.object(service, "client") as mock_client:
        mock_client.audio.transcriptions.create.side_effect = Exception("Connection failed")

        success, message = service.test_connection()

        assert success is False
        assert "error" in message.lower()


@pytest.mark.parametrize(
    "filename,expected_ext",
    [
        ("test.mp3", ".mp3"),
        ("audio.wav", ".wav"),
        ("recording.webm", ".webm"),
        ("file.m4a", ".m4a"),
        ("noextension", ".webm"),
    ],
)
def test_file_extension_variations(filename, expected_ext):
    """Test various file extension scenarios."""
    service = WhisperService(openai_api_key="test_key")
    assert service._get_file_extension(filename) == expected_ext


def test_transcribe_audio_file_cleanup(mock_whisper_response, sample_audio_data):
    """Test that temporary files are properly cleaned up."""
    service = WhisperService(openai_api_key="test_key")

    with patch.object(service, "client") as mock_client:
        mock_client.audio.transcriptions.create.return_value = mock_whisper_response

        # Track temporary files created during test
        original_temp_files = set()
        temp_dir = Path(tempfile.gettempdir())
        if temp_dir.exists():
            original_temp_files = {f.name for f in temp_dir.iterdir() if f.is_file()}

        # Execute transcription
        service.transcribe_audio(sample_audio_data, "test.wav")

        # Check that no new temporary files remain
        current_temp_files = set()
        if temp_dir.exists():
            current_temp_files = {f.name for f in temp_dir.iterdir() if f.is_file()}

        # Should be no new files (cleanup worked)
        new_files = current_temp_files - original_temp_files
        # Filter out any system files that might have been created
        audio_temp_files = [f for f in new_files if "tmp" in f.lower()]
        assert len(audio_temp_files) == 0, f"Temporary files not cleaned up: {audio_temp_files}"
