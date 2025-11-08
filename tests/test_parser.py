"""
Tests for the markdown parser.
"""

import os
import tempfile

import pytest

from backend.parser import parse_flashcard_content, parse_flashcard_file, validate_flashcard_file


def test_parse_basic_flashcard():
    """Test parsing a basic flashcard."""
    content = """
## Question 1
What is Python?

### Answer
Python is a high-level programming language.

---
"""
    flashcards = parse_flashcard_content(content)

    assert len(flashcards) == 1
    assert flashcards[0]["question"] == "What is Python?"
    assert flashcards[0]["answer"] == "Python is a high-level programming language."


def test_parse_multiple_flashcards():
    """Test parsing multiple flashcards."""
    content = """
## Question 1
What is Python?

### Answer
Python is a high-level programming language.

---

## Question 2
What is JavaScript?

### Answer
JavaScript is a scripting language for web browsers.

---
"""
    flashcards = parse_flashcard_content(content)

    assert len(flashcards) == 2
    assert flashcards[0]["question"] == "What is Python?"
    assert flashcards[1]["question"] == "What is JavaScript?"


def test_parse_without_question_number():
    """Test parsing flashcards without 'Question N' prefix."""
    content = """
## What is the difference between @staticmethod and @classmethod in Python?

### Answer
@staticmethod doesn't receive any implicit first argument (no self, no cls).
@classmethod receives the class as implicit first argument (cls).

---
"""
    flashcards = parse_flashcard_content(content)

    assert len(flashcards) == 1
    assert "What is the difference" in flashcards[0]["question"]
    assert "@staticmethod" in flashcards[0]["answer"]


def test_parse_multiline_answer():
    """Test parsing flashcards with multiline answers."""
    content = """
## Explain MVCC in PostgreSQL

### Answer
MVCC (Multi-Version Concurrency Control) allows multiple transactions to access the same data concurrently.
Each transaction sees a snapshot of the database at a specific point in time.
Old row versions are kept until no transaction needs them (then VACUUM cleans them up).
This avoids locking for reads and provides transaction isolation.

---
"""
    flashcards = parse_flashcard_content(content)

    assert len(flashcards) == 1
    assert "MVCC" in flashcards[0]["answer"]
    assert "VACUUM" in flashcards[0]["answer"]
    assert "transaction isolation" in flashcards[0]["answer"]


def test_parse_empty_content():
    """Test parsing empty content."""
    content = ""
    flashcards = parse_flashcard_content(content)

    assert len(flashcards) == 0


def test_parse_missing_answer():
    """Test parsing flashcard with missing answer section."""
    content = """
## What is Python?

This is just text without an answer section.

---
"""
    flashcards = parse_flashcard_content(content)

    # Should not create a flashcard if answer is missing
    assert len(flashcards) == 0


def test_parse_missing_question():
    """Test parsing content with answer but no question."""
    content = """
### Answer
This is an answer without a question.

---
"""
    flashcards = parse_flashcard_content(content)

    # Should not create a flashcard if question is missing
    assert len(flashcards) == 0


def test_parse_with_asterisk_separator():
    """Test parsing with *** separator instead of ---."""
    content = """
## Question 1
What is Python?

### Answer
Python is a programming language.

***

## Question 2
What is Java?

### Answer
Java is a programming language.

***
"""
    flashcards = parse_flashcard_content(content)

    assert len(flashcards) == 2


def test_parse_case_insensitive_answer():
    """Test that 'answer' and 'Answer' both work."""
    content = """
## Question 1
What is Python?

### answer
Python is a programming language.

---
"""
    flashcards = parse_flashcard_content(content)

    assert len(flashcards) == 1
    assert flashcards[0]["answer"] == "Python is a programming language."


def test_parse_flashcard_file(tmp_path):
    """Test parsing a flashcard from a file."""
    # Create a temporary file
    file_path = tmp_path / "test_flashcards.md"
    file_path.write_text("""
## What is 2+2?

### Answer
4

---
""")

    flashcards = parse_flashcard_file(str(file_path))

    assert len(flashcards) == 1
    assert flashcards[0]["question"] == "What is 2+2?"
    assert flashcards[0]["answer"] == "4"


def test_validate_valid_file(tmp_path):
    """Test validating a valid flashcard file."""
    file_path = tmp_path / "valid.md"
    file_path.write_text("""
## Question 1
What is Python?

### Answer
A programming language.

---
""")

    is_valid, message = validate_flashcard_file(str(file_path))

    assert is_valid is True
    assert "1 flashcard" in message


def test_validate_empty_file(tmp_path):
    """Test validating an empty file."""
    file_path = tmp_path / "empty.md"
    file_path.write_text("")

    is_valid, message = validate_flashcard_file(str(file_path))

    assert is_valid is False
    assert "No valid flashcards" in message


def test_validate_nonexistent_file():
    """Test validating a file that doesn't exist."""
    is_valid, message = validate_flashcard_file("/nonexistent/file.md")

    assert is_valid is False
    assert "not found" in message.lower()


def test_parse_complex_formatting():
    """Test parsing flashcards with complex markdown formatting."""
    content = """
## What are Python decorators?

### Answer
Decorators are functions that modify the behavior of other functions.

Example:
```python
@decorator
def my_function():
    pass
```

They are commonly used for:
- Logging
- Authentication
- Caching

---
"""
    flashcards = parse_flashcard_content(content)

    assert len(flashcards) == 1
    assert "decorators" in flashcards[0]["question"].lower()
    assert "Decorators are functions" in flashcards[0]["answer"]
    assert "```python" in flashcards[0]["answer"]
    assert "Logging" in flashcards[0]["answer"]
