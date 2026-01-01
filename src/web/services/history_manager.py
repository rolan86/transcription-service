"""
SQLite-based history manager for storing transcription records.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import threading


@dataclass
class HistoryEntry:
    """Represents a transcription history entry."""
    id: int
    created_at: str
    audio_filename: str
    duration_seconds: Optional[float]
    language: Optional[str]
    model: Optional[str]
    transcript_text: str
    word_count: int
    confidence: Optional[float]
    speaker_count: int


class HistoryManager:
    """
    Singleton manager for transcription history storage.
    Uses SQLite with FTS5 for full-text search.
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
        self._db_path = self._get_db_path()
        self._max_entries = 100
        self._init_database()

    def _get_db_path(self) -> Path:
        """Get the database path, creating directory if needed."""
        history_dir = Path.home() / ".transcription"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir / "history.db"

    @property
    def db_path(self) -> Path:
        """Public accessor for database path."""
        return self._db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Create main table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcription_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    audio_filename TEXT NOT NULL,
                    duration_seconds REAL,
                    language TEXT,
                    model TEXT,
                    transcript_text TEXT,
                    word_count INTEGER,
                    confidence REAL,
                    speaker_count INTEGER DEFAULT 0
                )
            """)

            # Create index on created_at for efficient sorting
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON transcription_history(created_at DESC)
            """)

            # Create FTS5 virtual table for full-text search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS transcription_fts USING fts5(
                    transcript_text,
                    audio_filename,
                    content='transcription_history',
                    content_rowid='id'
                )
            """)

            # Create triggers to keep FTS in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS history_ai AFTER INSERT ON transcription_history BEGIN
                    INSERT INTO transcription_fts(rowid, transcript_text, audio_filename)
                    VALUES (new.id, new.transcript_text, new.audio_filename);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS history_ad AFTER DELETE ON transcription_history BEGIN
                    INSERT INTO transcription_fts(transcription_fts, rowid, transcript_text, audio_filename)
                    VALUES ('delete', old.id, old.transcript_text, old.audio_filename);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS history_au AFTER UPDATE ON transcription_history BEGIN
                    INSERT INTO transcription_fts(transcription_fts, rowid, transcript_text, audio_filename)
                    VALUES ('delete', old.id, old.transcript_text, old.audio_filename);
                    INSERT INTO transcription_fts(rowid, transcript_text, audio_filename)
                    VALUES (new.id, new.transcript_text, new.audio_filename);
                END
            """)

            conn.commit()
        finally:
            conn.close()

    def save_transcription(self, result: Dict[str, Any], filename: str) -> int:
        """
        Save a transcription result to history.

        Returns the ID of the new entry.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Extract data from result
            text = result.get("text", "")
            word_count = len(text.split()) if text else 0
            duration = result.get("duration") or result.get("processing_time")
            language = result.get("language")
            confidence = result.get("confidence")

            # Get speaker count if available
            speaker_count = 0
            if result.get("speaker_detection", {}).get("enabled"):
                speakers = result.get("speaker_detection", {}).get("speakers", [])
                speaker_count = len(speakers)

            # Get model from metadata if available
            model = None
            if result.get("metadata"):
                model = result["metadata"].get("transcription", {}).get("model")

            cursor.execute("""
                INSERT INTO transcription_history
                (audio_filename, duration_seconds, language, model, transcript_text,
                 word_count, confidence, speaker_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                filename,
                duration,
                language,
                model,
                text,
                word_count,
                confidence,
                speaker_count,
            ))

            entry_id = cursor.lastrowid
            conn.commit()

            # Cleanup old entries if over limit
            self._cleanup_old_entries(conn)

            # Index for semantic search if available
            try:
                from .semantic_search import SemanticSearchService
                from .embedding_service import is_available as embeddings_available
                if embeddings_available() and text:
                    semantic_service = SemanticSearchService(str(self._db_path))
                    semantic_service.index_transcript(entry_id, text)
            except Exception as idx_err:
                print(f"Warning: Failed to index transcript for semantic search: {idx_err}")

            return entry_id
        finally:
            conn.close()

    def _cleanup_old_entries(self, conn: sqlite3.Connection):
        """Delete oldest entries if over the max limit."""
        cursor = conn.cursor()

        # Get current count
        cursor.execute("SELECT COUNT(*) FROM transcription_history")
        count = cursor.fetchone()[0]

        if count > self._max_entries:
            # Delete oldest entries
            delete_count = count - self._max_entries
            cursor.execute("""
                DELETE FROM transcription_history
                WHERE id IN (
                    SELECT id FROM transcription_history
                    ORDER BY created_at ASC
                    LIMIT ?
                )
            """, (delete_count,))
            conn.commit()

    def get_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get paginated history entries, most recent first."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, created_at, audio_filename, duration_seconds,
                       language, model, transcript_text, word_count,
                       confidence, speaker_count
                FROM transcription_history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all history entries (for reindexing)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, created_at, audio_filename, duration_seconds,
                       language, model, transcript_text, word_count,
                       confidence, speaker_count
                FROM transcription_history
                ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def search_history(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search history using full-text search."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Use FTS5 MATCH for full-text search
            cursor.execute("""
                SELECT h.id, h.created_at, h.audio_filename, h.duration_seconds,
                       h.language, h.model, h.transcript_text, h.word_count,
                       h.confidence, h.speaker_count
                FROM transcription_history h
                JOIN transcription_fts fts ON h.id = fts.rowid
                WHERE transcription_fts MATCH ?
                ORDER BY h.created_at DESC
                LIMIT ?
            """, (query, limit))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def get_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """Get a single history entry by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, created_at, audio_filename, duration_seconds,
                       language, model, transcript_text, word_count,
                       confidence, speaker_count
                FROM transcription_history
                WHERE id = ?
            """, (entry_id,))

            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
        finally:
            conn.close()

    def delete_entry(self, entry_id: int) -> bool:
        """Delete a history entry by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM transcription_history WHERE id = ?",
                (entry_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def clear_history(self) -> int:
        """Clear all history entries. Returns count of deleted entries."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transcription_history")
            count = cursor.fetchone()[0]

            cursor.execute("DELETE FROM transcription_history")
            conn.commit()
            return count
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM transcription_history")
            total_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT SUM(word_count), AVG(confidence), SUM(duration_seconds)
                FROM transcription_history
            """)
            row = cursor.fetchone()

            return {
                "total_entries": total_count,
                "max_entries": self._max_entries,
                "total_words": row[0] or 0,
                "average_confidence": round(row[1] or 0, 2),
                "total_duration_seconds": round(row[2] or 0, 1),
            }
        finally:
            conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary."""
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "audio_filename": row["audio_filename"],
            "duration_seconds": row["duration_seconds"],
            "language": row["language"],
            "model": row["model"],
            "transcript_text": row["transcript_text"],
            "word_count": row["word_count"],
            "confidence": row["confidence"],
            "speaker_count": row["speaker_count"],
            # Add preview (first 200 chars)
            "preview": (row["transcript_text"] or "")[:200] + ("..." if len(row["transcript_text"] or "") > 200 else ""),
        }
