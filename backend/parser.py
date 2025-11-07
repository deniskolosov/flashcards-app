"""
Markdown parser for flashcard files.

Expected format:
## Question
What is the difference between @staticmethod and @classmethod in Python?

### Answer
@staticmethod doesn't receive any implicit first argument.
@classmethod receives the class as implicit first argument (cls).

---
"""
import re


def parse_flashcard_file(file_path: str) -> list[dict[str, str]]:
    """
    Parse a markdown file containing flashcards.

    Args:
        file_path: Path to the markdown file

    Returns:
        List of flashcard dictionaries with 'question' and 'answer' keys
    """
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    return parse_flashcard_content(content)


def parse_flashcard_content(content: str) -> list[dict[str, str]]:
    """
    Parse markdown content containing flashcards.

    Args:
        content: Markdown string content

    Returns:
        List of flashcard dictionaries with 'question' and 'answer' keys
    """
    flashcards = []

    # Split by horizontal rules first, then process each section
    # Handle both --- and *** as separators
    sections = re.split(r'\n---+\n|\n\*\*\*+\n', content)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Look for ## heading (question) and ### Answer
        # Match ## (with optional "Question N" text) followed by content
        question_match = re.search(
            r'^##\s+(.+?)(?=\n###|\Z)',
            section,
            re.MULTILINE | re.DOTALL
        )

        # Match ### Answer followed by content
        answer_match = re.search(
            r'###\s+[Aa]nswer\s*\n(.+?)(?=\n##|\Z)',
            section,
            re.MULTILINE | re.DOTALL
        )

        if question_match and answer_match:
            question_text = question_match.group(1).strip()
            answer_text = answer_match.group(1).strip()

            # Remove "Question N" prefix if present
            question_text = re.sub(r'^[Qq]uestion\s+\d+\s*\n', '', question_text).strip()

            flashcards.append({
                'question': question_text,
                'answer': answer_text
            })

    return flashcards


def validate_flashcard_file(file_path: str) -> tuple[bool, str]:
    """
    Validate a flashcard file format.

    Args:
        file_path: Path to the markdown file

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        flashcards = parse_flashcard_file(file_path)

        if not flashcards:
            return False, "No valid flashcards found in file"

        for i, card in enumerate(flashcards):
            if not card['question']:
                return False, f"Card {i+1} has empty question"
            if not card['answer']:
                return False, f"Card {i+1} has empty answer"

        return True, f"Valid file with {len(flashcards)} flashcard(s)"

    except FileNotFoundError:
        return False, "File not found"
    except Exception as e:
        return False, f"Error parsing file: {e!s}"
