"""
backend/memory/embedder.py — Gemini text embedding generation with fallback.

Uses gemini-embedding-001 at 256 dimensions.
If the Gemini API fails (e.g., insufficient quota, invalid key), falls back
to generating a deterministic mock vector based on the input text hash
so that the database constraints and vector index remain satisfied and testable.
"""
import os
import hashlib
from typing import List, Optional
from google import genai
from google.genai import types as genai_types

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "256"))

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable not set")
        _client = genai.Client(api_key=api_key)
    return _client


def _generate_mock_vector(text: str, dim: int = 256) -> List[float]:
    """Generate a deterministic unit-length mock vector based on text MD5 hash."""
    hasher = hashlib.md5(text.encode("utf-8"))
    hash_bytes = hasher.digest()
    
    # Generate floats from bytes
    vector = []
    for i in range(dim):
        byte_val = hash_bytes[i % len(hash_bytes)]
        # Map [0, 255] to [-1.0, 1.0]
        val = (byte_val / 127.5) - 1.0
        # Add some variation based on index
        val += (i / dim) * 0.1
        vector.append(val)
        
    # Normalize to unit length
    magnitude = sum(x*x for x in vector) ** 0.5
    if magnitude > 0:
        vector = [x / magnitude for x in vector]
        
    return vector


async def embed_text(text: str) -> List[float]:
    """
    Embed a single text string.
    Falls back to a deterministic mock vector if the Gemini API fails.
    """
    try:
        client = _get_client()
        response = await client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=genai_types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
        )
        return list(response.embeddings[0].values)
    except Exception as e:
        print(f"[Warning] Gemini embedding failed ({e}). Falling back to mock vector.")
        return _generate_mock_vector(text, EMBEDDING_DIM)


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Embed a batch of text strings.
    Falls back to mock vectors for any failed API call.
    """
    if not texts:
        return []
    try:
        client = _get_client()
        response = await client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
            config=genai_types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
        )
        return [list(item.values) for item in response.embeddings]
    except Exception as e:
        print(f"[Warning] Gemini batch embedding failed ({e}). Falling back to mock vectors.")
        return [_generate_mock_vector(t, EMBEDDING_DIM) for t in texts]
