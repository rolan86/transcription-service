"""
Vocabulary manager for storing and retrieving custom vocabulary.
Stores vocabulary in ~/.transcription/vocabulary.txt
"""

from pathlib import Path
from typing import List, Optional
import threading


class VocabularyManager:
    """
    Singleton manager for custom vocabulary storage.
    Stores vocabulary as one word/phrase per line.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._vocab_path = self._get_vocab_path()

    def _get_vocab_path(self) -> Path:
        """Get the vocabulary file path, creating directory if needed."""
        vocab_dir = Path.home() / ".transcription"
        vocab_dir.mkdir(parents=True, exist_ok=True)
        return vocab_dir / "vocabulary.txt"

    def get_vocabulary(self) -> List[str]:
        """
        Get the list of vocabulary words/phrases.

        Returns:
            List of vocabulary terms
        """
        if not self._vocab_path.exists():
            return []

        try:
            with open(self._vocab_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Strip whitespace and filter empty lines
                return [line.strip() for line in lines if line.strip()]
        except Exception:
            return []

    def save_vocabulary(self, vocabulary: List[str]) -> bool:
        """
        Save vocabulary list to file.

        Args:
            vocabulary: List of vocabulary terms

        Returns:
            True if saved successfully
        """
        try:
            # Clean and deduplicate vocabulary
            cleaned = []
            seen = set()
            for term in vocabulary:
                term = term.strip()
                if term and term.lower() not in seen:
                    cleaned.append(term)
                    seen.add(term.lower())

            with open(self._vocab_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cleaned))
            return True
        except Exception:
            return False

    def add_term(self, term: str) -> bool:
        """
        Add a single term to vocabulary.

        Args:
            term: Term to add

        Returns:
            True if added successfully
        """
        term = term.strip()
        if not term:
            return False

        vocabulary = self.get_vocabulary()
        # Check for duplicates (case-insensitive)
        if term.lower() in [v.lower() for v in vocabulary]:
            return False

        vocabulary.append(term)
        return self.save_vocabulary(vocabulary)

    def remove_term(self, term: str) -> bool:
        """
        Remove a term from vocabulary.

        Args:
            term: Term to remove

        Returns:
            True if removed successfully
        """
        vocabulary = self.get_vocabulary()
        term_lower = term.strip().lower()
        new_vocabulary = [v for v in vocabulary if v.lower() != term_lower]

        if len(new_vocabulary) == len(vocabulary):
            return False  # Term not found

        return self.save_vocabulary(new_vocabulary)

    def clear_vocabulary(self) -> bool:
        """
        Clear all vocabulary.

        Returns:
            True if cleared successfully
        """
        return self.save_vocabulary([])

    def get_initial_prompt(self) -> Optional[str]:
        """
        Get the initial prompt string for Whisper.
        Formats vocabulary as a prompt for better recognition.

        Returns:
            Initial prompt string or None if no vocabulary
        """
        vocabulary = self.get_vocabulary()
        if not vocabulary:
            return None

        # Format as a conditioning prompt for Whisper
        # This helps the model recognize these terms
        terms = ', '.join(vocabulary)
        return f"The following terms may appear in the audio: {terms}."

    def get_vocabulary_text(self) -> str:
        """
        Get vocabulary as newline-separated text.

        Returns:
            Vocabulary text
        """
        return '\n'.join(self.get_vocabulary())

    def set_vocabulary_text(self, text: str) -> bool:
        """
        Set vocabulary from newline-separated text.

        Args:
            text: Vocabulary text (one term per line)

        Returns:
            True if saved successfully
        """
        lines = text.split('\n')
        vocabulary = [line.strip() for line in lines if line.strip()]
        return self.save_vocabulary(vocabulary)
