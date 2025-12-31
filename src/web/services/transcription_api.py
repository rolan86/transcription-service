"""
API adapter layer wrapping the core TranscriptionService.
Provides async interface for web API use.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.transcription_service import TranscriptionService
from config.settings import Settings
from utils.logger import setup_logger


class TranscriptionAPI:
    """Adapter layer between web API and core transcription service."""

    _instance: Optional["TranscriptionAPI"] = None
    _executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=2)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.settings = Settings()
        self.logger = setup_logger("web-api")
        self._service: Optional[TranscriptionService] = None
        self._initialized = True

    @property
    def service(self) -> TranscriptionService:
        """Lazy initialization of transcription service."""
        if self._service is None:
            self._service = TranscriptionService(self.settings, self.logger)
        return self._service

    def update_settings(
        self,
        model: str = "base",
        language: Optional[str] = None,
        enable_speakers: bool = False,
        num_speakers: Optional[int] = None,
        enable_preprocessing: bool = False,
        initial_prompt: Optional[str] = None,
    ) -> None:
        """Update settings for transcription."""
        # Force re-create service with new settings on next use
        self._service = None

        self.settings.config["transcription"]["default_model"] = model
        self.settings.config["transcription"]["default_language"] = language
        self.settings.config["transcription"]["initial_prompt"] = initial_prompt
        self.settings.config["enhancement"]["enable_speaker_detection"] = enable_speakers
        self.settings.config["enhancement"]["expected_speakers"] = num_speakers
        self.settings.config["enhancement"]["enable_audio_preprocessing"] = enable_preprocessing

    async def transcribe_file(
        self,
        file_path: str,
        output_format: str = "json",
        model: str = "base",
        language: Optional[str] = None,
        enable_speakers: bool = False,
        num_speakers: Optional[int] = None,
        enable_preprocessing: bool = False,
        use_vocabulary: bool = False,
    ) -> Dict[str, Any]:
        """
        Transcribe a file asynchronously.

        Args:
            file_path: Path to the audio/video file
            output_format: Output format (txt, json, srt, vtt)
            model: Whisper model size
            language: Language code (None for auto-detect)
            enable_speakers: Enable speaker detection
            num_speakers: Expected number of speakers
            enable_preprocessing: Enable audio preprocessing
            use_vocabulary: Use custom vocabulary from vocabulary manager

        Returns:
            Transcription result dictionary
        """
        # Get initial prompt from vocabulary if enabled
        initial_prompt = None
        if use_vocabulary:
            from .vocabulary_manager import VocabularyManager
            vocab_manager = VocabularyManager()
            initial_prompt = vocab_manager.get_initial_prompt()

        # Update settings
        self.update_settings(
            model=model,
            language=language,
            enable_speakers=enable_speakers,
            num_speakers=num_speakers,
            enable_preprocessing=enable_preprocessing,
            initial_prompt=initial_prompt,
        )

        # Run transcription in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self.service.transcribe_file(
                input_file=file_path,
                output_format=output_format,
            ),
        )

        return result

    async def save_upload_file(self, file_content: bytes, filename: str) -> str:
        """
        Save uploaded file content to a temporary file.

        Args:
            file_content: Raw file bytes
            filename: Original filename

        Returns:
            Path to the saved temporary file
        """
        # Get file extension
        ext = Path(filename).suffix.lower()

        # Create temp file with correct extension
        fd, temp_path = tempfile.mkstemp(suffix=ext)
        try:
            os.write(fd, file_content)
        finally:
            os.close(fd)

        return temp_path

    def cleanup_temp_file(self, file_path: str) -> None:
        """Clean up a temporary file."""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass

    def get_supported_formats(self) -> Dict[str, list]:
        """Get supported input formats."""
        return {
            "audio": [".mp3", ".wav", ".m4a", ".flac"],
            "video": [".mp4", ".mov", ".avi"],
        }

    def get_available_models(self) -> list:
        """Get available Whisper models with info."""
        return [
            {
                "name": "tiny",
                "description": "Fastest, lowest accuracy",
                "size_mb": 75,
                "relative_speed": 1.0,
            },
            {
                "name": "base",
                "description": "Good balance of speed and accuracy",
                "size_mb": 142,
                "relative_speed": 0.7,
            },
            {
                "name": "small",
                "description": "Better accuracy, slower",
                "size_mb": 466,
                "relative_speed": 0.4,
            },
            {
                "name": "medium",
                "description": "High accuracy",
                "size_mb": 1500,
                "relative_speed": 0.2,
            },
            {
                "name": "large",
                "description": "Best accuracy, slowest",
                "size_mb": 2900,
                "relative_speed": 0.1,
            },
        ]

    def get_output_formats(self) -> list:
        """Get supported output formats."""
        return ["txt", "json", "srt", "vtt"]
