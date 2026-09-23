import logging

from sentence_transformers import SentenceTransformer

from backend.config import settings
from backend.models import EMBEDDING_DIM

logger = logging.getLogger(__name__)


class BGEEmbedder:
    def __init__(self):
        # Load embedding model from environment variables
        # Reference: https://sbert.net/docs/quickstart.html#sentence-transformer
        logger.info("Loading embedding model %s", settings.embedding_model)
        self.model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model %s loaded", settings.embedding_model)

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single text string into a normalised 768-dim vector.
        Returns normalised embedding vector for semantic search.
        """
        # Strip whitespace before embedding
        normalised = text.strip()
        if not normalised:
            logger.warning("Cannot embed empty text")
            raise ValueError("Cannot embed because empty text")

        # Encode text into a normalised vector
        embedding = self.model.encode(normalised, normalize_embeddings=True)
        vector = embedding.tolist()

        # Verify if embedding dimensions match the database schema
        if len(vector) != EMBEDDING_DIM:
            logger.error(
                "Embedding dimension mismatch (model=%s): expected %s, got %s",
                settings.embedding_model,
                EMBEDDING_DIM,
                len(vector),
            )
            raise ValueError(
                f"Embedding dimensions does not match: Expected {EMBEDDING_DIM} but got {len(vector)}"
            )

        logger.debug(
            "Embedded text (chars=%s, dim=%s)",
            len(normalised),
            len(vector),
        )
        return vector


# Shared embedder instance
_embedder: BGEEmbedder | None = None


def get_embedder() -> BGEEmbedder:
    """Return the shared BGE embedder instance."""
    global _embedder
    if _embedder is None:
        # Create the BGE embedder instance
        _embedder = BGEEmbedder()
    return _embedder