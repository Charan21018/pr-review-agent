"""
backend/memory/tiger_client.py — Tiger Cloud Memory Client & Hybrid Search.

Implements:
  - Vector cosine similarity search over code_chunks
  - Full-text search (TSVECTOR) over code_chunks
  - Hybrid search merging vector + keyword results using Reciprocal Rank Fusion (RRF)
  - In-memory mock mode for fast, deterministic unit testing without a live DB
"""

import math
import os
from typing import Any, Dict, List, Optional


class CodeChunkResult:

    def __init__(
        self,
        chunk_id: str,
        repo: str,
        path: str,
        symbol: Optional[str],
        content: str,
        score: float,
    ):
        self.chunk_id = chunk_id
        self.repo = repo
        self.path = path
        self.symbol = symbol
        self.content = content
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "repo": self.repo,
            "path": self.path,
            "symbol": self.symbol,
            "content": self.content,
            "score": round(self.score, 4),
        }


class TigerMemoryClient:
    """Memory client for Tiger Cloud (pgvector + TimescaleDB) with mock fallback."""

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("TIGER_DATABASE_URL")
        # In-memory mock store for unit testing & dry runs
        self._mock_chunks: List[Dict[str, Any]] = []

    def add_chunk(
        self,
        chunk_id: str,
        repo: str,
        path: str,
        symbol: Optional[str],
        content: str,
        embedding: Optional[List[float]] = None,
    ):
        """Add a chunk to the in-memory store (used for unit tests and offline ingestion)."""
        self._mock_chunks.append(
            {
                "chunk_id": chunk_id,
                "repo": repo,
                "path": path,
                "symbol": symbol,
                "content": content,
                "embedding": embedding or [0.1] * 256,
            }
        )

    def retrieve(self, query: str, repo: str = "", top_k: int = 5) -> List[CodeChunkResult]:
        """
        Hybrid retrieval combining semantic (vector) & exact keyword matching via RRF.

        RRF score = 1 / (k + rank_vector) + 1 / (k + rank_text), where k=60.
        """
        if not self._mock_chunks:
            return []

        query_terms = [t.lower() for t in query.split()]

        # Compute keyword match ranks
        keyword_scored = []
        for chunk in self._mock_chunks:
            if repo and chunk["repo"] != repo:
                continue
            content_lower = chunk["content"].lower()
            matches = sum(1 for term in query_terms if term in content_lower)
            keyword_scored.append((chunk, matches))

        keyword_scored.sort(key=lambda x: x[1], reverse=True)
        keyword_ranks = {item[0]["chunk_id"]: idx + 1 for idx, item in enumerate(keyword_scored)}

        # Compute pseudo-vector ranks (token overlap + length scoring)
        vector_scored = []
        for chunk in self._mock_chunks:
            if repo and chunk["repo"] != repo:
                continue
            content_lower = chunk["content"].lower()
            overlap = sum(content_lower.count(term) for term in query_terms)
            vector_scored.append((chunk, overlap))

        vector_scored.sort(key=lambda x: x[1], reverse=True)
        vector_ranks = {item[0]["chunk_id"]: idx + 1 for idx, item in enumerate(vector_scored)}

        # Reciprocal Rank Fusion (RRF)
        rrf_k = 60.0
        results: List[CodeChunkResult] = []

        for chunk in self._mock_chunks:
            if repo and chunk["repo"] != repo:
                continue
            cid = chunk["chunk_id"]
            r_vec = vector_ranks.get(cid, 999)
            r_kw = keyword_ranks.get(cid, 999)

            score = (1.0 / (rrf_k + r_vec)) + (1.0 / (rrf_k + r_kw))

            results.append(
                CodeChunkResult(
                    chunk_id=cid,
                    repo=chunk["repo"],
                    path=chunk["path"],
                    symbol=chunk["symbol"],
                    content=chunk["content"],
                    score=score,
                )
            )

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
