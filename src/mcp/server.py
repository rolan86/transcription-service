"""
MCP Server for the Transcription Service.

Provides tools for transcribing audio/video files, searching history,
and analyzing transcripts using AI.
"""

import os
import sys
import logging
from typing import Optional
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP(
    name="transcription-service",
    instructions="Transcription service with AI-powered analysis capabilities. Use these tools to transcribe audio/video files, search history, and analyze transcripts."
)

# Configure logging (never use print in STDIO servers)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Transcription Tools
# ============================================================================

@mcp.tool()
async def transcribe_file(
    file_path: str,
    model: str = "base",
    language: Optional[str] = None,
    enable_speakers: bool = False,
) -> str:
    """
    Transcribe a local audio or video file.

    Args:
        file_path: Absolute path to the audio/video file
        model: Whisper model size (tiny, base, small, medium, large)
        language: Language code (e.g., 'en', 'es') or None for auto-detect
        enable_speakers: Enable speaker diarization

    Returns:
        The transcribed text
    """
    from src.core.transcriber import Transcriber
    from src.config.settings import Config

    # Validate file exists
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    # Validate file extension
    valid_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.mp4', '.mov', '.avi', '.webm'}
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in valid_extensions:
        return f"Error: Unsupported file format: {ext}. Supported: {', '.join(valid_extensions)}"

    try:
        config = Config()
        transcriber = Transcriber(config)

        result = transcriber.transcribe(
            file_path,
            model_name=model,
            language=language,
            enable_diarization=enable_speakers,
        )

        if result.get("error"):
            return f"Error: {result['error']}"

        text = result.get("text", "")

        # Add speaker labels if available
        if enable_speakers and result.get("segments"):
            lines = []
            current_speaker = None
            for seg in result["segments"]:
                speaker = seg.get("speaker", "")
                if speaker and speaker != current_speaker:
                    lines.append(f"\n[{speaker}]")
                    current_speaker = speaker
                lines.append(seg.get("text", "").strip())
            text = " ".join(lines)

        return text or "No transcription produced."

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return f"Error during transcription: {str(e)}"


@mcp.tool()
async def transcribe_url(
    url: str,
    model: str = "base",
    language: Optional[str] = None,
) -> str:
    """
    Transcribe audio from a YouTube or Vimeo URL.

    Args:
        url: YouTube or Vimeo video URL
        model: Whisper model size (tiny, base, small, medium, large)
        language: Language code (e.g., 'en', 'es') or None for auto-detect

    Returns:
        The transcribed text
    """
    import tempfile
    import yt_dlp
    from src.core.transcriber import Transcriber
    from src.config.settings import Config

    # Validate URL
    valid_domains = ['youtube.com', 'youtu.be', 'vimeo.com']
    if not any(domain in url.lower() for domain in valid_domains):
        return f"Error: Unsupported URL. Only YouTube and Vimeo are supported."

    try:
        # Download audio to temp file
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "audio.%(ext)s")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find the downloaded file
            audio_file = os.path.join(temp_dir, "audio.mp3")
            if not os.path.exists(audio_file):
                return "Error: Failed to download audio from URL."

            # Transcribe
            config = Config()
            transcriber = Transcriber(config)

            result = transcriber.transcribe(
                audio_file,
                model_name=model,
                language=language,
            )

            if result.get("error"):
                return f"Error: {result['error']}"

            return result.get("text", "No transcription produced.")

    except Exception as e:
        logger.error(f"URL transcription error: {e}")
        return f"Error during URL transcription: {str(e)}"


# ============================================================================
# History/Search Tools
# ============================================================================

@mcp.tool()
async def search_transcripts(
    query: str,
    limit: int = 10,
) -> str:
    """
    Search through transcription history.

    Args:
        query: Search query (searches in transcript text and filenames)
        limit: Maximum number of results to return

    Returns:
        Search results with transcript IDs and snippets
    """
    from src.web.services.history_manager import HistoryManager

    try:
        manager = HistoryManager()
        results = manager.search_history(query, limit=limit)

        if not results:
            return f"No transcripts found matching '{query}'."

        output_lines = [f"Found {len(results)} transcript(s) matching '{query}':\n"]

        for entry in results:
            output_lines.append(f"ID: {entry['id']}")
            output_lines.append(f"File: {entry.get('filename', 'Unknown')}")
            output_lines.append(f"Date: {entry.get('created_at', 'Unknown')}")

            # Show snippet of text
            text = entry.get('transcript_text', '')[:200]
            if len(entry.get('transcript_text', '')) > 200:
                text += "..."
            output_lines.append(f"Preview: {text}")
            output_lines.append("-" * 40)

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error searching transcripts: {str(e)}"


@mcp.tool()
async def get_transcript(transcript_id: int) -> str:
    """
    Retrieve a transcript by its ID.

    Args:
        transcript_id: The unique ID of the transcript

    Returns:
        The full transcript text and metadata
    """
    from src.web.services.history_manager import HistoryManager

    try:
        manager = HistoryManager()
        entry = manager.get_entry(transcript_id)

        if not entry:
            return f"Error: Transcript with ID {transcript_id} not found."

        output_lines = [
            f"Transcript ID: {entry['id']}",
            f"Filename: {entry.get('filename', 'Unknown')}",
            f"Language: {entry.get('language', 'Unknown')}",
            f"Model: {entry.get('model', 'Unknown')}",
            f"Duration: {entry.get('duration', 0):.1f} seconds",
            f"Created: {entry.get('created_at', 'Unknown')}",
            "",
            "--- Transcript ---",
            entry.get('transcript_text', 'No text available'),
        ]

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"Get transcript error: {e}")
        return f"Error retrieving transcript: {str(e)}"


@mcp.tool()
async def list_recent_transcripts(limit: int = 10) -> str:
    """
    List recent transcriptions from history.

    Args:
        limit: Maximum number of entries to return

    Returns:
        List of recent transcripts with IDs and summaries
    """
    from src.web.services.history_manager import HistoryManager

    try:
        manager = HistoryManager()
        entries = manager.get_recent_entries(limit=limit)

        if not entries:
            return "No transcriptions in history."

        output_lines = [f"Recent {len(entries)} transcript(s):\n"]

        for entry in entries:
            output_lines.append(f"ID: {entry['id']}")
            output_lines.append(f"File: {entry.get('filename', 'Unknown')}")
            output_lines.append(f"Date: {entry.get('created_at', 'Unknown')}")
            output_lines.append(f"Duration: {entry.get('duration', 0):.1f}s")

            # Show preview
            text = entry.get('transcript_text', '')[:100]
            if len(entry.get('transcript_text', '')) > 100:
                text += "..."
            output_lines.append(f"Preview: {text}")
            output_lines.append("-" * 40)

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"List transcripts error: {e}")
        return f"Error listing transcripts: {str(e)}"


# ============================================================================
# AI Analysis Tools
# ============================================================================

@mcp.tool()
async def cleanup_transcript(
    text: str,
    provider: Optional[str] = None,
) -> str:
    """
    Clean up a transcript using AI.
    Removes filler words (um, uh, like), fixes punctuation, and corrects grammar.

    Args:
        text: The transcript text to clean up
        provider: AI provider to use ('zai', 'claude', 'llama') or None for auto

    Returns:
        The cleaned transcript text
    """
    from src.web.services.ai_provider import AIProviderFactory
    from src.web.services.cleanup_service import CleanupService

    try:
        ai_provider = AIProviderFactory.create_default(provider)
        if not ai_provider:
            return "Error: No AI providers available. Configure API keys in settings."

        cleanup_service = CleanupService(ai_provider)
        result = await cleanup_service.cleanup(text)

        return result.get("cleaned", text)

    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return f"Error during cleanup: {str(e)}"


@mcp.tool()
async def summarize_transcript(
    text: str,
    length: str = "medium",
    provider: Optional[str] = None,
) -> str:
    """
    Generate a summary of a transcript.

    Args:
        text: The transcript text to summarize
        length: Summary length - 'short', 'medium', or 'long'
        provider: AI provider to use ('zai', 'claude', 'llama') or None for auto

    Returns:
        The summary text
    """
    from src.web.services.ai_provider import AIProviderFactory
    from src.web.services.extraction_service import ExtractionService

    try:
        ai_provider = AIProviderFactory.create_default(provider)
        if not ai_provider:
            return "Error: No AI providers available. Configure API keys in settings."

        extraction_service = ExtractionService(ai_provider)
        summary = await extraction_service.summarize(text, length)

        return summary

    except Exception as e:
        logger.error(f"Summarize error: {e}")
        return f"Error during summarization: {str(e)}"


@mcp.tool()
async def extract_key_points(
    text: str,
    max_points: int = 5,
    provider: Optional[str] = None,
) -> str:
    """
    Extract key points from a transcript.

    Args:
        text: The transcript text to analyze
        max_points: Maximum number of key points to extract
        provider: AI provider to use ('zai', 'claude', 'llama') or None for auto

    Returns:
        List of key points
    """
    from src.web.services.ai_provider import AIProviderFactory
    from src.web.services.extraction_service import ExtractionService

    try:
        ai_provider = AIProviderFactory.create_default(provider)
        if not ai_provider:
            return "Error: No AI providers available. Configure API keys in settings."

        extraction_service = ExtractionService(ai_provider)
        points = await extraction_service.extract_key_points(text, max_points)

        if not points:
            return "No key points extracted."

        return "\n".join(f"- {point}" for point in points)

    except Exception as e:
        logger.error(f"Key points error: {e}")
        return f"Error extracting key points: {str(e)}"


@mcp.tool()
async def extract_action_items(
    text: str,
    provider: Optional[str] = None,
) -> str:
    """
    Extract action items and tasks from a transcript.

    Args:
        text: The transcript text to analyze
        provider: AI provider to use ('zai', 'claude', 'llama') or None for auto

    Returns:
        List of action items with assignees (if mentioned)
    """
    from src.web.services.ai_provider import AIProviderFactory
    from src.web.services.extraction_service import ExtractionService

    try:
        ai_provider = AIProviderFactory.create_default(provider)
        if not ai_provider:
            return "Error: No AI providers available. Configure API keys in settings."

        extraction_service = ExtractionService(ai_provider)
        items = await extraction_service.extract_action_items(text)

        if not items:
            return "No action items found."

        output_lines = []
        for item in items:
            action = item.get('action', '')
            assignee = item.get('assignee')
            if assignee:
                output_lines.append(f"[ ] {action} (Assigned to: {assignee})")
            else:
                output_lines.append(f"[ ] {action}")

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"Action items error: {e}")
        return f"Error extracting action items: {str(e)}"


@mcp.tool()
async def generate_meeting_notes(
    text: str,
    provider: Optional[str] = None,
) -> str:
    """
    Generate formatted meeting notes from a transcript.

    Args:
        text: The transcript text to process
        provider: AI provider to use ('zai', 'claude', 'llama') or None for auto

    Returns:
        Formatted meeting notes in Markdown
    """
    from src.web.services.ai_provider import AIProviderFactory
    from src.web.services.extraction_service import ExtractionService

    try:
        ai_provider = AIProviderFactory.create_default(provider)
        if not ai_provider:
            return "Error: No AI providers available. Configure API keys in settings."

        extraction_service = ExtractionService(ai_provider)
        notes = await extraction_service.generate_meeting_notes(text)

        return notes

    except Exception as e:
        logger.error(f"Meeting notes error: {e}")
        return f"Error generating meeting notes: {str(e)}"


@mcp.tool()
async def full_analysis(
    text: str,
    provider: Optional[str] = None,
) -> str:
    """
    Run comprehensive analysis on a transcript.
    Includes summary, key points, action items, entities, and topics.

    Args:
        text: The transcript text to analyze
        provider: AI provider to use ('zai', 'claude', 'llama') or None for auto

    Returns:
        Complete analysis results
    """
    from src.web.services.ai_provider import AIProviderFactory
    from src.web.services.extraction_service import ExtractionService

    try:
        ai_provider = AIProviderFactory.create_default(provider)
        if not ai_provider:
            return "Error: No AI providers available. Configure API keys in settings."

        extraction_service = ExtractionService(ai_provider)
        results = await extraction_service.full_analysis(text)

        output_lines = ["# Transcript Analysis\n"]

        # Summary
        if results.get("summary"):
            output_lines.append("## Summary")
            output_lines.append(results["summary"])
            output_lines.append("")

        # Key Points
        if results.get("key_points"):
            output_lines.append("## Key Points")
            for point in results["key_points"]:
                output_lines.append(f"- {point}")
            output_lines.append("")

        # Action Items
        if results.get("action_items"):
            output_lines.append("## Action Items")
            for item in results["action_items"]:
                action = item.get('action', '')
                assignee = item.get('assignee')
                if assignee:
                    output_lines.append(f"- [ ] {action} (@{assignee})")
                else:
                    output_lines.append(f"- [ ] {action}")
            output_lines.append("")

        # Entities
        if results.get("entities"):
            entities = results["entities"]
            has_entities = any(entities.get(cat) for cat in entities)
            if has_entities:
                output_lines.append("## Entities")
                for category, items in entities.items():
                    if items:
                        output_lines.append(f"**{category.title()}**: {', '.join(items)}")
                output_lines.append("")

        # Topics
        if results.get("topics"):
            output_lines.append("## Topics")
            for topic in results["topics"]:
                name = topic.get('topic', '')
                relevance = topic.get('relevance', 'medium')
                output_lines.append(f"- {name} [{relevance}]")
            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"Full analysis error: {e}")
        return f"Error during analysis: {str(e)}"


# ============================================================================
# Main entry point
# ============================================================================

def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
