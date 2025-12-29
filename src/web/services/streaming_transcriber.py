"""
Streaming transcriber for real-time WebSocket transcription.
Processes audio chunks and returns incremental results.
"""

import asyncio
import tempfile
import os
import io
import struct
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poc.transcription_engine import TranscriptionEngine


@dataclass
class AudioBuffer:
    """Buffer for accumulating audio data."""

    sample_rate: int = 16000
    channels: int = 1
    bytes_per_sample: int = 2  # 16-bit audio
    chunks: List[bytes] = field(default_factory=list)

    def add_chunk(self, data: bytes) -> None:
        """Add audio chunk to buffer."""
        self.chunks.append(data)

    def get_duration(self) -> float:
        """Get total duration in seconds."""
        total_bytes = sum(len(chunk) for chunk in self.chunks)
        samples = total_bytes / self.bytes_per_sample / self.channels
        return samples / self.sample_rate

    def get_audio_data(self) -> bytes:
        """Get concatenated audio data."""
        return b"".join(self.chunks)

    def clear(self) -> None:
        """Clear the buffer."""
        self.chunks.clear()

    def shift(self, keep_duration: float = 1.0) -> None:
        """
        Remove old data, keeping only the last `keep_duration` seconds.
        Used for overlapping context in streaming.
        """
        total_duration = self.get_duration()
        if total_duration <= keep_duration:
            return

        # Calculate bytes to keep
        bytes_to_keep = int(keep_duration * self.sample_rate * self.channels * self.bytes_per_sample)

        # Get all data and keep only the last portion
        all_data = self.get_audio_data()
        if len(all_data) > bytes_to_keep:
            self.chunks = [all_data[-bytes_to_keep:]]
        else:
            self.chunks = [all_data]


class StreamingTranscriber:
    """
    Real-time streaming transcriber using Whisper.
    Processes audio in chunks and returns incremental transcription.
    """

    _executor = ThreadPoolExecutor(max_workers=2)

    def __init__(
        self,
        model_size: str = "base",
        language: Optional[str] = None,
        sample_rate: int = 16000,
        chunk_duration: float = 5.0,
    ):
        """
        Initialize streaming transcriber.

        Args:
            model_size: Whisper model size
            language: Language code (None for auto-detect)
            sample_rate: Expected audio sample rate
            chunk_duration: Duration of chunks to process (seconds)
        """
        self.model_size = model_size
        self.language = language
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.overlap_duration = 1.0  # 1 second overlap for context

        self._engine: Optional[TranscriptionEngine] = None
        self._buffer = AudioBuffer(sample_rate=sample_rate)
        self._full_transcript: List[str] = []
        self._temp_files: List[str] = []

    @property
    def engine(self) -> TranscriptionEngine:
        """Lazy initialization of transcription engine."""
        if self._engine is None:
            self._engine = TranscriptionEngine(model_size=self.model_size)
        return self._engine

    async def process_audio_chunk(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Process an audio chunk and return transcription if enough data accumulated.

        Args:
            audio_data: Raw PCM audio data (16-bit, mono)

        Returns:
            Transcription result dict or None if more data needed
        """
        # Add to buffer
        self._buffer.add_chunk(audio_data)

        # Check if we have enough data to transcribe
        duration = self._buffer.get_duration()
        if duration < self.chunk_duration:
            return None

        # Transcribe the buffer
        result = await self._transcribe_buffer()

        # Keep some overlap for context continuity
        self._buffer.shift(keep_duration=self.overlap_duration)

        return result

    async def _transcribe_buffer(self) -> Dict[str, Any]:
        """Transcribe the current buffer contents."""
        # Save buffer to temp WAV file
        temp_path = await self._save_buffer_to_wav()
        self._temp_files.append(temp_path)

        try:
            # Run transcription in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                lambda: self.engine.transcribe_audio(temp_path, self.language),
            )

            text = result.get("text", "").strip()
            if text:
                self._full_transcript.append(text)

            return {
                "text": text,
                "is_final": False,
                "timestamp": self._buffer.get_duration(),
                "confidence": result.get("confidence", 0.0),
            }

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
                self._temp_files.remove(temp_path)
            except Exception:
                pass

    async def _save_buffer_to_wav(self) -> str:
        """Save current buffer to a WAV file."""
        audio_data = self._buffer.get_audio_data()

        # Create WAV file
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        try:
            # Write WAV header
            with os.fdopen(fd, "wb") as f:
                self._write_wav(f, audio_data)
        except Exception:
            os.close(fd)
            raise

        return temp_path

    def _write_wav(self, f, audio_data: bytes) -> None:
        """Write WAV file with header."""
        num_channels = 1
        sample_width = 2  # 16-bit
        num_frames = len(audio_data) // sample_width

        # WAV header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(audio_data)))  # File size - 8
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # Subchunk1 size
        f.write(struct.pack("<H", 1))  # Audio format (PCM)
        f.write(struct.pack("<H", num_channels))
        f.write(struct.pack("<I", self.sample_rate))
        f.write(struct.pack("<I", self.sample_rate * num_channels * sample_width))  # Byte rate
        f.write(struct.pack("<H", num_channels * sample_width))  # Block align
        f.write(struct.pack("<H", sample_width * 8))  # Bits per sample
        f.write(b"data")
        f.write(struct.pack("<I", len(audio_data)))
        f.write(audio_data)

    async def finalize(self) -> Dict[str, Any]:
        """
        Finalize transcription by processing any remaining audio.

        Returns:
            Final transcription result
        """
        # Process any remaining audio in buffer
        if self._buffer.get_duration() > 0.5:  # At least 0.5 seconds
            result = await self._transcribe_buffer()
            if result and result.get("text"):
                # Already added to full_transcript in _transcribe_buffer
                pass

        # Combine all transcripts
        full_text = " ".join(self._full_transcript)

        return {
            "text": full_text,
            "is_final": True,
            "segments": [],  # Could be enhanced to include segment info
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        # Clear buffer
        self._buffer.clear()
        self._full_transcript.clear()

        # Remove any remaining temp files
        for temp_path in self._temp_files:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception:
                pass
        self._temp_files.clear()


def convert_webm_to_pcm(webm_data: bytes, sample_rate: int = 16000) -> bytes:
    """
    Convert WebM/Opus audio to raw PCM.
    This is a placeholder - actual implementation would use ffmpeg or similar.

    For browser recording, we'll use the Web Audio API to send PCM directly,
    or use a JavaScript library to convert.
    """
    # In practice, the frontend will handle conversion using Web Audio API
    # and send raw PCM data. This function is here for future use if needed.
    return webm_data
