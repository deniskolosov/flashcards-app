"""
Whisper transcription service for converting audio to text.
Supports OpenAI Whisper API for speech-to-text functionality.
"""

import tempfile
from pathlib import Path

from openai import OpenAI

from backend.schemas import TranscriptionResponse


class WhisperService:
    """Service for audio transcription using OpenAI Whisper."""

    def __init__(
        self,
        openai_api_key: str | None = None,
        model: str = "whisper-1",
    ):
        self.openai_api_key = openai_api_key
        self.model = model
        self.client = None

        if openai_api_key:
            self.client = OpenAI(api_key=openai_api_key)

    def transcribe_audio(
        self, audio_data: bytes, filename: str = "audio.webm"
    ) -> TranscriptionResponse:
        """
        Transcribe audio data to text using OpenAI Whisper.

        Args:
            audio_data: Raw audio file data as bytes
            filename: Original filename (used for format detection)

        Returns:
            TranscriptionResponse with transcribed text

        Raises:
            ValueError: If no OpenAI API key is configured
            Exception: If transcription fails
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        if not audio_data:
            raise ValueError("No audio data provided")

        try:
            # Create a temporary file for the audio data
            with tempfile.NamedTemporaryFile(
                suffix=self._get_file_extension(filename), delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()

                # Use Path to ensure proper file handling
                temp_path = Path(temp_file.name)

                try:
                    # Transcribe the audio file
                    with open(temp_path, "rb") as audio_file:
                        response = self.client.audio.transcriptions.create(
                            model=self.model, file=audio_file, response_format="text"
                        )

                    # Clean up the transcribed text
                    transcribed_text = self._clean_transcription(response)

                    return TranscriptionResponse(text=transcribed_text, confidence=None)

                finally:
                    # Clean up the temporary file
                    if temp_path.exists():
                        temp_path.unlink()

        except Exception as e:
            raise Exception(f"Error transcribing audio: {e!s}") from e

    def _get_file_extension(self, filename: str) -> str:
        """
        Get appropriate file extension based on filename.

        Args:
            filename: Original filename

        Returns:
            File extension with dot (e.g., '.webm', '.mp3')
        """
        # Extract extension from filename or default to .webm
        if "." in filename:
            return "." + filename.split(".")[-1].lower()
        return ".webm"

    def _clean_transcription(self, transcription: str) -> str:
        """
        Clean and normalize transcribed text.

        Args:
            transcription: Raw transcription from Whisper

        Returns:
            Cleaned transcription text
        """
        if not transcription:
            return ""

        # Remove leading/trailing whitespace
        text = transcription.strip()

        # Remove common Whisper artifacts
        if text.endswith("."):
            text = text[:-1]

        # Normalize whitespace
        text = " ".join(text.split())

        return text

    def test_connection(self) -> tuple[bool, str]:
        """
        Test API connection with a simple transcription.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.client:
            return False, "OpenAI API key not configured"

        try:
            # Create a minimal test audio file (1 second of silence in WAV format)
            # This is a minimal WAV file with 1 second of silence
            test_audio = self._create_test_audio()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(test_audio)
                temp_file.flush()

                temp_path = Path(temp_file.name)

                try:
                    with open(temp_path, "rb") as audio_file:
                        self.client.audio.transcriptions.create(
                            model=self.model, file=audio_file, response_format="text"
                        )

                    return True, "Whisper API connection successful"

                finally:
                    if temp_path.exists():
                        temp_path.unlink()

        except Exception as e:
            return False, f"Whisper API error: {e!s}"

    def _create_test_audio(self) -> bytes:
        """
        Create a minimal WAV file for testing purposes.

        Returns:
            Bytes representing a minimal WAV file with silence
        """
        # Minimal WAV file header for 1 second of silence at 8kHz, 16-bit mono
        # This creates a very small valid audio file for API testing
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
