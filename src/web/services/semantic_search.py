"""
Semantic search service for finding transcripts by meaning.
Uses local embeddings to enable similarity-based search.
"""

import sqlite3
import pickle
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from pathlib import Path

from .embedding_service import EmbeddingService, is_available as embeddings_available

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """Service for semantic (meaning-based) transcript search."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the semantic search service.

        Args:
            db_path: Path to the SQLite database (uses default if None)
        """
        if db_path is None:
            from .history_manager import HistoryManager
            db_path = HistoryManager().db_path

        self.db_path = db_path
        self.embedding_service = EmbeddingService()
        self._ensure_embeddings_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_embeddings_table(self):
        """Create the embeddings table if it doesn't exist."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transcript_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    history_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(history_id, chunk_index),
                    FOREIGN KEY (history_id) REFERENCES transcription_history(id)
                        ON DELETE CASCADE
                )
            """)
            # Create index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_history_id
                ON transcript_embeddings(history_id)
            """)
            conn.commit()
        finally:
            conn.close()

    def is_available(self) -> bool:
        """Check if semantic search is available."""
        return embeddings_available()

    def index_transcript(self, history_id: int, transcript_text: str) -> bool:
        """
        Index a transcript for semantic search.

        Args:
            history_id: ID of the transcript in history
            transcript_text: The transcript text to index

        Returns:
            True if successful, False otherwise
        """
        if not transcript_text:
            return False

        try:
            # Generate chunks and embeddings
            chunks_data = self.embedding_service.embed_and_chunk(transcript_text)

            if not chunks_data:
                return False

            conn = self._get_connection()
            try:
                # Delete existing embeddings for this transcript
                conn.execute(
                    "DELETE FROM transcript_embeddings WHERE history_id = ?",
                    (history_id,)
                )

                # Insert new embeddings
                for chunk in chunks_data:
                    embedding_blob = pickle.dumps(chunk['embedding'])
                    conn.execute(
                        """
                        INSERT INTO transcript_embeddings
                        (history_id, chunk_index, chunk_text, embedding)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            history_id,
                            chunk['chunk_index'],
                            chunk['chunk_text'],
                            embedding_blob,
                        )
                    )

                conn.commit()
                logger.info(f"Indexed transcript {history_id} with {len(chunks_data)} chunks")
                return True

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error indexing transcript {history_id}: {e}")
            return False

    def delete_index(self, history_id: int) -> bool:
        """
        Delete embeddings for a transcript.

        Args:
            history_id: ID of the transcript

        Returns:
            True if successful
        """
        conn = self._get_connection()
        try:
            conn.execute(
                "DELETE FROM transcript_embeddings WHERE history_id = ?",
                (history_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def search(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Search transcripts by semantic similarity.

        Args:
            query: The search query
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of search results with similarity scores
        """
        if not query:
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)

            conn = self._get_connection()
            try:
                # Get all embeddings
                cursor = conn.execute("""
                    SELECT e.id, e.history_id, e.chunk_index, e.chunk_text, e.embedding,
                           h.filename, h.created_at, h.language, h.duration
                    FROM transcript_embeddings e
                    JOIN transcription_history h ON e.history_id = h.id
                """)

                rows = cursor.fetchall()
                if not rows:
                    return []

                # Calculate similarities
                results = []
                seen_history_ids = set()

                for row in rows:
                    embedding = pickle.loads(row['embedding'])
                    similarity = self.embedding_service.cosine_similarity(
                        query_embedding, embedding
                    )

                    if similarity >= min_similarity:
                        history_id = row['history_id']

                        # Keep only the best match per transcript
                        if history_id in seen_history_ids:
                            # Check if this chunk has better similarity
                            for i, r in enumerate(results):
                                if r['history_id'] == history_id:
                                    if similarity > r['similarity']:
                                        results[i] = {
                                            'history_id': history_id,
                                            'filename': row['filename'],
                                            'created_at': row['created_at'],
                                            'language': row['language'],
                                            'duration': row['duration'],
                                            'chunk_text': row['chunk_text'],
                                            'chunk_index': row['chunk_index'],
                                            'similarity': similarity,
                                        }
                                    break
                        else:
                            seen_history_ids.add(history_id)
                            results.append({
                                'history_id': history_id,
                                'filename': row['filename'],
                                'created_at': row['created_at'],
                                'language': row['language'],
                                'duration': row['duration'],
                                'chunk_text': row['chunk_text'],
                                'chunk_index': row['chunk_index'],
                                'similarity': similarity,
                            })

                # Sort by similarity and limit
                results.sort(key=lambda x: x['similarity'], reverse=True)
                return results[:limit]

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    def get_indexed_count(self) -> int:
        """Get the number of indexed transcripts."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT history_id) FROM transcript_embeddings"
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_total_chunks(self) -> int:
        """Get the total number of indexed chunks."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM transcript_embeddings")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def reindex_all(self) -> Dict[str, int]:
        """
        Reindex all transcripts in history.

        Returns:
            Dict with 'success' and 'failed' counts
        """
        from .history_manager import HistoryManager

        manager = HistoryManager()
        entries = manager.get_all_entries()

        success = 0
        failed = 0

        for entry in entries:
            history_id = entry['id']
            transcript_text = entry.get('transcript_text', '')

            if transcript_text:
                if self.index_transcript(history_id, transcript_text):
                    success += 1
                else:
                    failed += 1
            else:
                failed += 1

        logger.info(f"Reindexed {success} transcripts, {failed} failed")
        return {'success': success, 'failed': failed}

    def is_indexed(self, history_id: int) -> bool:
        """Check if a transcript is already indexed."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM transcript_embeddings WHERE history_id = ?",
                (history_id,)
            )
            return cursor.fetchone()[0] > 0
        finally:
            conn.close()
