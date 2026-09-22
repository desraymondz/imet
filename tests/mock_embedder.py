# Helper for the mock embedder to return deterministic vectors

from backend.models import EMBEDDING_DIM


def topic_vector(text: str) -> list[float]:
    """
    Mock BGEEmbedder.embed_text

    - Two texts sharing a topic have a cosine similarity of 1
    - Texts with no shared topic have 0
    - Text with no topic at all uses a spare dimension so it matches nothing
    """
    vector = [0.0] * EMBEDDING_DIM
    
    # Each topic word turns on its own dimension when the text contains it
    for index, topic in enumerate(["hiking", "finance", "music"]):
        if topic in text.lower():
            vector[index] = 1.0

    # No known topic: use a spare dimension so it matches nothing
    if not any(vector):
        vector[-1] = 1.0
    return vector