"""
Embedding service for generating text embeddings using local models.
Uses sentence-transformers for offline, API-free embedding generation.
"""

import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Model will be loaded lazily to avoid startup delay
_model = None
_model_name = "all-MiniLM-L6-v2"  # 384 dimensions, fast, good quality


def get_embedding_model():
    """Get or initialize the embedding model (lazy loading)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {_model_name}")
            _model = SentenceTransformer(_model_name)
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


class EmbeddingService:
    """Service for generating and managing text embeddings."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize the embedding service.

        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._model = None

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            self._model = get_embedding_model()
        return self._model

    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by the model."""
        return 384  # all-MiniLM-L6-v2 produces 384-dimensional embeddings

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text: The text to chunk

        Returns:
            List of text chunks
        """
        if not text:
            return []

        # Clean the text
        text = text.strip()
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # If not at the end, try to break at a sentence or word boundary
            if end < len(text):
                # Try to find a sentence boundary
                for boundary in ['. ', '! ', '? ', '\n\n', '\n']:
                    boundary_pos = text.rfind(boundary, start + self.chunk_size // 2, end)
                    if boundary_pos != -1:
                        end = boundary_pos + len(boundary)
                        break
                else:
                    # Fall back to word boundary
                    space_pos = text.rfind(' ', start + self.chunk_size // 2, end)
                    if space_pos != -1:
                        end = space_pos + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
            # Ensure we make progress
            if start <= end - self.chunk_size:
                start = end

        return chunks

    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate an embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            Embedding vector as numpy array
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of texts to embed

        Returns:
            2D numpy array of embeddings (n_texts x embedding_dim)
        """
        if not texts:
            return np.array([])

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings

    def embed_and_chunk(self, text: str) -> List[dict]:
        """
        Chunk text and generate embeddings for each chunk.

        Args:
            text: The text to process

        Returns:
            List of dicts with 'chunk_index', 'chunk_text', and 'embedding'
        """
        chunks = self.chunk_text(text)
        if not chunks:
            return []

        embeddings = self.embed_texts(chunks)

        results = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            results.append({
                'chunk_index': i,
                'chunk_text': chunk,
                'embedding': embedding,
            })

        return results

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def batch_cosine_similarity(query: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity between a query and multiple embeddings.

        Args:
            query: Query embedding vector
            embeddings: 2D array of embeddings to compare against

        Returns:
            Array of similarity scores
        """
        if embeddings.size == 0:
            return np.array([])

        # Normalize query
        query_norm = query / (np.linalg.norm(query) + 1e-10)

        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_norm = embeddings / (norms + 1e-10)

        # Compute similarities
        similarities = np.dot(embeddings_norm, query_norm)
        return similarities


def is_available() -> bool:
    """Check if the embedding service is available."""
    try:
        from sentence_transformers import SentenceTransformer
        return True
    except ImportError:
        return False
