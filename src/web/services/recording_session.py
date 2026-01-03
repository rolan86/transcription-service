"""
Recording session management for long-duration live recordings.
Handles server-side audio chunk persistence to prevent browser memory overflow.
"""

import os
import tempfile
import struct
import uuid
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import threading


@dataclass
class SessionChunk:
    """Represents a saved audio chunk."""
    path: str
    start_time: float
    duration: float
    size_bytes: int


@dataclass
class RecordingSession:
    """
    A recording session that persists audio chunks to disk.
    Designed for recordings over 1 hour that would exceed browser memory.
    """
    session_id: str
    sample_rate: int = 16000
    channels: int = 1
    bytes_per_sample: int = 2
    created_at: float = field(default_factory=time.time)
    chunks: List[SessionChunk] = field(default_factory=list)
    total_duration: float = 0.0
    _temp_dir: Optional[str] = None
    # For session continuation
    is_paused: bool = False
    paused_at: Optional[float] = None
    transcript_text: str = ""
    chapters: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        """Create temp directory for session."""
        self._temp_dir = tempfile.mkdtemp(prefix=f"recording_session_{self.session_id}_")

    def add_chunk(self, audio_data: bytes) -> SessionChunk:
        """
        Save an audio chunk to disk.

        Args:
            audio_data: Raw PCM audio data

        Returns:
            SessionChunk with chunk metadata
        """
        # Calculate duration
        samples = len(audio_data) / self.bytes_per_sample / self.channels
        duration = samples / self.sample_rate

        # Save to file
        chunk_path = os.path.join(
            self._temp_dir,
            f"chunk_{len(self.chunks):04d}.raw"
        )

        with open(chunk_path, 'wb') as f:
            f.write(audio_data)

        chunk = SessionChunk(
            path=chunk_path,
            start_time=self.total_duration,
            duration=duration,
            size_bytes=len(audio_data),
        )

        self.chunks.append(chunk)
        self.total_duration += duration

        return chunk

    def get_all_audio(self) -> bytes:
        """
        Read and concatenate all audio chunks.

        Returns:
            Combined raw PCM audio data
        """
        all_data = []
        for chunk in self.chunks:
            if os.path.exists(chunk.path):
                with open(chunk.path, 'rb') as f:
                    all_data.append(f.read())
        return b''.join(all_data)

    def save_as_wav(self, output_path: str) -> str:
        """
        Save all chunks as a single WAV file.

        Args:
            output_path: Path to save the WAV file

        Returns:
            Path to the saved file
        """
        audio_data = self.get_all_audio()

        with open(output_path, 'wb') as f:
            self._write_wav_header(f, len(audio_data))
            f.write(audio_data)

        return output_path

    def save_as_wav_temp(self) -> str:
        """
        Save all chunks as a temporary WAV file.

        Returns:
            Path to the temporary WAV file
        """
        fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix="session_audio_")
        os.close(fd)
        return self.save_as_wav(temp_path)

    def _write_wav_header(self, f, data_size: int) -> None:
        """Write WAV file header."""
        num_channels = self.channels
        sample_width = self.bytes_per_sample

        # WAV header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))  # File size - 8
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # Subchunk1 size
        f.write(struct.pack("<H", 1))  # Audio format (PCM)
        f.write(struct.pack("<H", num_channels))
        f.write(struct.pack("<I", self.sample_rate))
        f.write(struct.pack("<I", self.sample_rate * num_channels * sample_width))
        f.write(struct.pack("<H", num_channels * sample_width))
        f.write(struct.pack("<H", sample_width * 8))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))

    def cleanup(self) -> None:
        """Remove all temporary files and directory."""
        for chunk in self.chunks:
            try:
                if os.path.exists(chunk.path):
                    os.unlink(chunk.path)
            except Exception:
                pass

        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                os.rmdir(self._temp_dir)
            except Exception:
                pass

        self.chunks.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        total_bytes = sum(c.size_bytes for c in self.chunks)
        return {
            'session_id': self.session_id,
            'chunk_count': len(self.chunks),
            'total_duration': self.total_duration,
            'total_bytes': total_bytes,
            'duration_formatted': self._format_duration(self.total_duration),
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def pause_session(self, transcript: str = "") -> None:
        """
        Pause the session for potential continuation.

        Args:
            transcript: Current transcript text to save
        """
        self.is_paused = True
        self.paused_at = time.time()
        if transcript:
            self.transcript_text = transcript

    def resume_session(self) -> Dict[str, Any]:
        """
        Resume a paused session.

        Returns:
            Dict with prior_duration and prior_transcript
        """
        self.is_paused = False
        self.paused_at = None
        return {
            'prior_duration': self.total_duration,
            'prior_duration_formatted': self._format_duration(self.total_duration),
            'prior_transcript': self.transcript_text,
            'prior_chapters': self.chapters,
        }

    def get_continuation_state(self) -> Dict[str, Any]:
        """Get state needed to continue recording."""
        return {
            'session_id': self.session_id,
            'total_duration': self.total_duration,
            'duration_formatted': self._format_duration(self.total_duration),
            'transcript': self.transcript_text,
            'chapters': self.chapters,
            'chunk_count': len(self.chunks),
        }


class SessionManager:
    """
    Manages multiple recording sessions.
    Thread-safe singleton pattern.
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
        self._sessions: Dict[str, RecordingSession] = {}
        self._session_lock = threading.Lock()

    def create_session(self, sample_rate: int = 16000) -> RecordingSession:
        """
        Create a new recording session.

        Args:
            sample_rate: Audio sample rate

        Returns:
            New RecordingSession
        """
        session_id = str(uuid.uuid4())[:8]
        session = RecordingSession(
            session_id=session_id,
            sample_rate=sample_rate,
        )

        with self._session_lock:
            self._sessions[session_id] = session

        return session

    def get_session(self, session_id: str) -> Optional[RecordingSession]:
        """Get a session by ID."""
        with self._session_lock:
            return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """Remove and cleanup a session."""
        with self._session_lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.cleanup()

    def pause_session(self, session_id: str, transcript: str = "") -> Optional[RecordingSession]:
        """
        Pause a session for potential continuation instead of removing it.

        Args:
            session_id: Session ID to pause
            transcript: Current transcript text to save

        Returns:
            The paused session or None if not found
        """
        with self._session_lock:
            session = self._sessions.get(session_id)
            if session:
                session.pause_session(transcript)
            return session

    def get_paused_session(self, session_id: str) -> Optional[RecordingSession]:
        """
        Get a paused session for continuation.

        Args:
            session_id: Session ID to retrieve

        Returns:
            The paused session or None
        """
        with self._session_lock:
            session = self._sessions.get(session_id)
            if session and session.is_paused:
                return session
            return None

    def cleanup_old_sessions(self, max_age_seconds: int = 3600) -> int:
        """
        Remove sessions older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds (default: 1 hour)

        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        to_remove = []

        with self._session_lock:
            for session_id, session in self._sessions.items():
                if current_time - session.created_at > max_age_seconds:
                    to_remove.append(session_id)

            for session_id in to_remove:
                session = self._sessions.pop(session_id, None)
                if session:
                    session.cleanup()

        return len(to_remove)

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get stats for all active sessions."""
        with self._session_lock:
            return [session.get_stats() for session in self._sessions.values()]
