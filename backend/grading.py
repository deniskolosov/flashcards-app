"""
AI grading service for comparing user answers with reference answers.
Supports both Anthropic Claude and OpenAI GPT models.
"""
import json

from anthropic import Anthropic
from openai import OpenAI

from backend.schemas import GradingResult

GRADING_SYSTEM_PROMPT = """You are a flashcard grading assistant. Your job is to compare a student's answer with a reference answer and provide constructive feedback.

Grade based on these criteria:
- **Perfect (90-100)**: Answer covers all key concepts accurately with good understanding
- **Good (70-89)**: Answer covers most key concepts with minor gaps or inaccuracies
- **Partial (40-69)**: Answer shows some understanding but misses important concepts
- **Wrong (0-39)**: Answer is mostly incorrect or shows fundamental misunderstanding

Provide your response in JSON format:
{
  "score": <number 0-100>,
  "grade": "<Perfect|Good|Partial|Wrong>",
  "feedback": "<detailed feedback explaining what was correct, what was missed, and what was wrong>",
  "key_concepts_covered": ["concept1", "concept2"],
  "key_concepts_missed": ["concept3"]
}

Be encouraging but honest. Focus on what the student got right, then explain what could be improved."""


class GradingService:
    """Service for grading flashcard answers using AI."""

    def __init__(
        self,
        anthropic_api_key: str | None = None,
        openai_api_key: str | None = None,
        default_provider: str = "anthropic",
        anthropic_model: str = "claude-sonnet-4-20250514",
        openai_model: str = "gpt-4o"
    ):
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.default_provider = default_provider
        self.anthropic_model = anthropic_model
        self.openai_model = openai_model

        # Initialize clients
        self.anthropic_client = None
        self.openai_client = None

        if anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=anthropic_api_key)

        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)

    def grade_answer(
        self,
        question: str,
        reference_answer: str,
        user_answer: str,
        provider: str | None = None
    ) -> GradingResult:
        """
        Grade a user's answer against the reference answer.

        Args:
            question: The flashcard question
            reference_answer: The reference answer from the flashcard
            user_answer: The user's submitted answer
            provider: Optional override for AI provider ("anthropic" or "openai")

        Returns:
            GradingResult with score, grade, and feedback

        Raises:
            ValueError: If no API key is configured for the provider
        """
        provider = provider or self.default_provider

        if provider == "anthropic":
            return self._grade_with_anthropic(question, reference_answer, user_answer)
        elif provider == "openai":
            return self._grade_with_openai(question, reference_answer, user_answer)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _grade_with_anthropic(
        self,
        question: str,
        reference_answer: str,
        user_answer: str
    ) -> GradingResult:
        """Grade using Anthropic Claude."""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")

        user_prompt = f"""Question: {question}

Reference Answer: {reference_answer}

Student's Answer: {user_answer}

Please grade the student's answer and provide feedback in JSON format."""

        try:
            response = self.anthropic_client.messages.create(
                model=self.anthropic_model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"{GRADING_SYSTEM_PROMPT}\n\n{user_prompt}"
                    }
                ]
            )

            # Parse the response
            response_text = response.content[0].text

            # Try to extract JSON from the response
            result_data = self._extract_json(response_text)

            return GradingResult(**result_data)

        except Exception as e:
            raise Exception(f"Error grading with Anthropic: {e!s}") from e

    def _grade_with_openai(
        self,
        question: str,
        reference_answer: str,
        user_answer: str
    ) -> GradingResult:
        """Grade using OpenAI GPT."""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        user_prompt = f"""Question: {question}

Reference Answer: {reference_answer}

Student's Answer: {user_answer}

Please grade the student's answer and provide feedback."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": GRADING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            # Parse the response
            response_text = response.choices[0].message.content
            result_data = json.loads(response_text)

            return GradingResult(**result_data)

        except Exception as e:
            raise Exception(f"Error grading with OpenAI: {e!s}") from e

    def _extract_json(self, text: str) -> dict:
        """
        Extract JSON from response text.
        Handles cases where JSON is wrapped in markdown code blocks.
        """
        # Try to parse as-is first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract from code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract valid JSON from response: {text}")

    def test_connection(self, provider: str | None = None) -> tuple[bool, str]:
        """
        Test API connection for a provider.

        Args:
            provider: Provider to test ("anthropic" or "openai"), defaults to default_provider

        Returns:
            Tuple of (success: bool, message: str)
        """
        provider = provider or self.default_provider

        try:
            # Use a simple test question
            self.grade_answer(
                question="What is 2+2?",
                reference_answer="4",
                user_answer="4",
                provider=provider
            )
            return True, f"{provider.capitalize()} API connection successful"
        except Exception as e:
            return False, f"{provider.capitalize()} API error: {e!s}"
