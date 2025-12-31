"""
Extraction service for transcript summarization and analysis.
Provides summaries, key points, action items, and entity extraction.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from .ai_provider import AIProvider


class ExtractionService:
    """Service for extracting insights from transcripts using AI."""

    def __init__(self, provider: AIProvider):
        """
        Initialize extraction service.

        Args:
            provider: AI provider to use for extraction
        """
        self.provider = provider

    async def summarize(
        self,
        transcript: str,
        length: str = "medium"
    ) -> str:
        """
        Generate a summary of the transcript.

        Args:
            transcript: Transcript text to summarize
            length: Summary length - 'short', 'medium', or 'long'

        Returns:
            Summary text
        """
        length_guide = {
            "short": "2-3 sentences",
            "medium": "1 paragraph (4-6 sentences)",
            "long": "2-3 paragraphs"
        }

        system_prompt = """You are a summarization assistant. Create clear, accurate summaries that capture the main points and key information. Do not add information that isn't in the original text."""

        prompt = f"""Summarize this transcript in {length_guide.get(length, length_guide['medium'])}:

{transcript}

Provide only the summary, no additional commentary."""

        return await self.provider.complete(prompt, system_prompt)

    async def extract_key_points(
        self,
        transcript: str,
        max_points: int = 5
    ) -> List[str]:
        """
        Extract main topics and key points from the transcript.

        Args:
            transcript: Transcript text to analyze
            max_points: Maximum number of key points to extract

        Returns:
            List of key point strings
        """
        system_prompt = """You are an analysis assistant. Extract the most important key points from text. Return your response as a JSON array of strings. Only output valid JSON, no additional text."""

        prompt = f"""Extract the {max_points} most important key points from this transcript.
Return as a JSON array of strings, like: ["point 1", "point 2", ...]

Transcript:
{transcript}"""

        response = await self.provider.complete(prompt, system_prompt)

        try:
            # Try to parse JSON response
            points = json.loads(response.strip())
            if isinstance(points, list):
                return points[:max_points]
        except json.JSONDecodeError:
            # Fall back to line-by-line parsing
            lines = response.strip().split('\n')
            points = []
            for line in lines:
                line = line.strip()
                # Remove common prefixes like "1.", "- ", "* "
                if line and not line.startswith('[') and not line.startswith(']'):
                    line = line.lstrip('0123456789.-*) ').strip()
                    if line:
                        points.append(line)
            return points[:max_points]

        return []

    async def extract_action_items(
        self,
        transcript: str
    ) -> List[Dict[str, Any]]:
        """
        Extract action items, tasks, and commitments from the transcript.

        Args:
            transcript: Transcript text to analyze

        Returns:
            List of action items with 'action' and optional 'assignee' fields
        """
        system_prompt = """You are a task extraction assistant. Identify action items, tasks, commitments, and to-dos from conversations. Return your response as a JSON array. Only output valid JSON, no additional text."""

        prompt = f"""Extract all action items, tasks, and commitments from this transcript.
For each item, identify who is responsible (if mentioned).
Return as a JSON array like: [{{"action": "description", "assignee": "person name or null"}}]

If there are no action items, return an empty array: []

Transcript:
{transcript}"""

        response = await self.provider.complete(prompt, system_prompt)

        try:
            items = json.loads(response.strip())
            if isinstance(items, list):
                # Validate structure
                validated = []
                for item in items:
                    if isinstance(item, dict) and 'action' in item:
                        validated.append({
                            'action': item.get('action', ''),
                            'assignee': item.get('assignee')
                        })
                return validated
        except json.JSONDecodeError:
            pass

        return []

    async def extract_entities(
        self,
        transcript: str
    ) -> Dict[str, List[str]]:
        """
        Extract named entities from the transcript.

        Args:
            transcript: Transcript text to analyze

        Returns:
            Dictionary with entity categories: people, organizations, locations, dates, products
        """
        system_prompt = """You are a named entity recognition assistant. Extract named entities from text and categorize them. Return your response as a JSON object. Only output valid JSON, no additional text."""

        prompt = f"""Extract named entities from this transcript.
Return as a JSON object with these categories:
{{"people": [], "organizations": [], "locations": [], "dates": [], "products": []}}

Only include entities that are actually mentioned. Use empty arrays for categories with no entities.

Transcript:
{transcript}"""

        response = await self.provider.complete(prompt, system_prompt)

        default_result = {
            "people": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "products": []
        }

        try:
            entities = json.loads(response.strip())
            if isinstance(entities, dict):
                # Merge with defaults to ensure all keys exist
                for key in default_result:
                    if key in entities and isinstance(entities[key], list):
                        default_result[key] = entities[key]
                return default_result
        except json.JSONDecodeError:
            pass

        return default_result

    async def extract_topics(
        self,
        transcript: str,
        max_topics: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract main topics discussed in the transcript.

        Args:
            transcript: Transcript text to analyze
            max_topics: Maximum number of topics to extract

        Returns:
            List of topics with 'topic' and 'relevance' fields
        """
        system_prompt = """You are a topic analysis assistant. Identify the main topics discussed in a conversation. Return your response as a JSON array. Only output valid JSON, no additional text."""

        prompt = f"""Identify the {max_topics} main topics discussed in this transcript.
For each topic, provide a brief label and a relevance score (high, medium, low).
Return as a JSON array like: [{{"topic": "topic name", "relevance": "high"}}]

Transcript:
{transcript}"""

        response = await self.provider.complete(prompt, system_prompt)

        try:
            topics = json.loads(response.strip())
            if isinstance(topics, list):
                validated = []
                for topic in topics[:max_topics]:
                    if isinstance(topic, dict) and 'topic' in topic:
                        validated.append({
                            'topic': topic.get('topic', ''),
                            'relevance': topic.get('relevance', 'medium')
                        })
                return validated
        except json.JSONDecodeError:
            pass

        return []

    async def full_analysis(
        self,
        transcript: str
    ) -> Dict[str, Any]:
        """
        Run comprehensive analysis on the transcript.
        Executes all extraction methods in parallel for efficiency.

        Args:
            transcript: Transcript text to analyze

        Returns:
            Dictionary with all analysis results
        """
        # Run all extractions in parallel
        results = await asyncio.gather(
            self.summarize(transcript, "medium"),
            self.extract_key_points(transcript, 5),
            self.extract_action_items(transcript),
            self.extract_entities(transcript),
            self.extract_topics(transcript, 5),
            return_exceptions=True
        )

        # Process results, handling any errors
        summary = results[0] if not isinstance(results[0], Exception) else ""
        key_points = results[1] if not isinstance(results[1], Exception) else []
        action_items = results[2] if not isinstance(results[2], Exception) else []
        entities = results[3] if not isinstance(results[3], Exception) else {}
        topics = results[4] if not isinstance(results[4], Exception) else []

        return {
            "summary": summary,
            "key_points": key_points,
            "action_items": action_items,
            "entities": entities,
            "topics": topics,
        }

    async def generate_meeting_notes(
        self,
        transcript: str
    ) -> str:
        """
        Generate formatted meeting notes from a transcript.

        Args:
            transcript: Transcript text to process

        Returns:
            Formatted meeting notes in Markdown
        """
        system_prompt = """You are a meeting notes assistant. Create well-organized meeting notes from transcripts. Format the output in Markdown with clear sections."""

        prompt = f"""Generate meeting notes from this transcript.

Include these sections:
## Summary
(Brief overview of the meeting)

## Key Discussion Points
(Main topics discussed)

## Decisions Made
(Any decisions or conclusions reached)

## Action Items
(Tasks assigned, with assignees if mentioned)

## Next Steps
(Any follow-up items or future plans mentioned)

Transcript:
{transcript}"""

        return await self.provider.complete(prompt, system_prompt)
