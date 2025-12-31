"""
Transcript cleanup service using AI providers.
Removes filler words, fixes punctuation and grammar.
"""

import re
from typing import Dict, Any, List
from .ai_provider import AIProvider


class CleanupService:
    """Service for cleaning up transcripts using AI."""

    SYSTEM_PROMPT = """You are a transcript cleanup assistant. Your job is to:
1. Remove filler words (um, uh, like, you know, basically, actually, literally, sort of, kind of)
2. Remove false starts and repeated words
3. Fix punctuation and capitalization
4. Correct obvious grammar errors
5. Keep the speaker's voice, tone, and meaning completely intact
6. Preserve all speaker labels (e.g., [SPEAKER_00]) exactly as they appear
7. Do NOT summarize, condense, or change the content
8. Do NOT add new information or interpretations

Return ONLY the cleaned transcript text, nothing else. No explanations, no commentary."""

    def __init__(self, provider: AIProvider):
        """
        Initialize cleanup service.

        Args:
            provider: AI provider to use for cleanup
        """
        self.provider = provider

    async def cleanup(self, transcript: str) -> Dict[str, Any]:
        """
        Clean up a transcript.

        Args:
            transcript: Raw transcript text

        Returns:
            Dictionary with original, cleaned text, and change metrics
        """
        if not transcript or not transcript.strip():
            return {
                "original": transcript,
                "cleaned": transcript,
                "changes_made": 0,
                "filler_words_removed": 0,
                "word_count_original": 0,
                "word_count_cleaned": 0,
            }

        prompt = f"Clean up this transcript:\n\n{transcript}"
        cleaned = await self.provider.complete(prompt, self.SYSTEM_PROMPT)

        # Calculate metrics
        original_words = len(transcript.split())
        cleaned_words = len(cleaned.split())
        filler_count = self._count_filler_words(transcript)

        return {
            "original": transcript,
            "cleaned": cleaned.strip(),
            "changes_made": abs(original_words - cleaned_words) + filler_count,
            "filler_words_removed": filler_count,
            "word_count_original": original_words,
            "word_count_cleaned": cleaned_words,
        }

    def _count_filler_words(self, text: str) -> int:
        """Count filler words in text."""
        filler_patterns = [
            r'\bum+\b',
            r'\buh+\b',
            r'\blike\b',
            r'\byou know\b',
            r'\bbasically\b',
            r'\bactually\b',
            r'\bliterally\b',
            r'\bsort of\b',
            r'\bkind of\b',
            r'\bi mean\b',
            r'\bso+\b(?=\s*,)',  # "so" followed by comma
        ]

        count = 0
        text_lower = text.lower()
        for pattern in filler_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            count += len(matches)

        return count

    async def cleanup_with_diff(self, transcript: str) -> Dict[str, Any]:
        """
        Clean up transcript and generate a diff-style comparison.

        Args:
            transcript: Raw transcript text

        Returns:
            Dictionary with original, cleaned, diff, and metrics
        """
        result = await self.cleanup(transcript)

        # Generate simple word-level diff
        original_words = result["original"].split()
        cleaned_words = result["cleaned"].split()

        diff = self._generate_diff(original_words, cleaned_words)
        result["diff"] = diff

        return result

    def _generate_diff(self, original: List[str], cleaned: List[str]) -> List[Dict[str, Any]]:
        """
        Generate a simple diff between original and cleaned text.

        Returns list of diff items: {type: 'same'|'removed'|'added', text: str}
        """
        diff = []

        # Simple diff - mark words that appear to be removed (fillers)
        filler_words = {
            'um', 'uh', 'umm', 'uhh', 'like', 'basically', 'actually',
            'literally', 'you', 'know', 'i', 'mean', 'so', 'kind', 'of', 'sort'
        }

        i = 0
        j = 0

        while i < len(original) and j < len(cleaned):
            orig_word = original[i].lower().strip('.,!?;:')
            clean_word = cleaned[j].lower().strip('.,!?;:')

            if orig_word == clean_word:
                diff.append({"type": "same", "text": original[i]})
                i += 1
                j += 1
            elif orig_word in filler_words:
                diff.append({"type": "removed", "text": original[i]})
                i += 1
            else:
                # Assume word was modified
                diff.append({"type": "removed", "text": original[i]})
                diff.append({"type": "added", "text": cleaned[j]})
                i += 1
                j += 1

        # Add remaining original words as removed
        while i < len(original):
            diff.append({"type": "removed", "text": original[i]})
            i += 1

        # Add remaining cleaned words as added
        while j < len(cleaned):
            diff.append({"type": "added", "text": cleaned[j]})
            j += 1

        return diff
