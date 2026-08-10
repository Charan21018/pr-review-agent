"""
backend/memory/context_retriever.py — Context Retriever performing hybrid search.

Fuses pgvector cosine similarity search and PostgreSQL full-text search (FTS)
using Reciprocal Rank Fusion (RRF).
"""
import re
from typing import List, Optional, Tuple

from backend.memory.embedder import embed_text
from backend.memory.tiger_client import search_chunks, search_chunks_fts


class ContextRetriever:
    """Retrieves relevant codebase context for specialist analysis."""

    def __init__(self, top_k: int = 6, rrf_constant: int = 60):
        self.top_k = top_k
        self.rrf_constant = rrf_constant

    def _extract_keywords(self, diff_text: str) -> str:
        """Extract key identifiers (class names, function names) to use as FTS queries."""
        # Simple extraction: find function and class definitions, and variable assignments
        matches = re.findall(r'\b(def|class|function|struct|func|interface)\s+([A-Za-z0-9_]+)', diff_text)
        keywords = [m[1] for m in matches]
        # Fallback to general words if no identifiers found
        if not keywords:
            words = re.findall(r'\b[A-Za-z0-9_]{4,15}\b', diff_text)
            keywords = words[:10]
        return " | ".join(keywords[:10])

    async def retrieve_context(self, pr_diff: str, repo: Optional[str] = None) -> List[str]:
        """Perform hybrid retrieval and return list of unique content chunks."""
        if not pr_diff.strip():
            return []

        # 1. Generate query embedding & run vector search
        try:
            query_embedding = await embed_text(pr_diff[:2000])  # embed first part of diff
            vector_results = await search_chunks(query_embedding, top_k=self.top_k, repo=repo)
        except Exception as e:
            print(f"[Warning] Vector search failed during retrieval: {e}")
            vector_results = []

        # 2. Extract keywords & run FTS search
        keywords = self._extract_keywords(pr_diff)
        if keywords:
            try:
                fts_results = await search_chunks_fts(keywords, top_k=self.top_k, repo=repo)
            except Exception as e:
                print(f"[Warning] FTS search failed during retrieval: {e}")
                fts_results = []
        else:
            fts_results = []

        # 3. Reciprocal Rank Fusion (RRF)
        # Result structures: list of (id, repo, path, symbol, chunk_index, content, [score/rrf])
        scores = {}
        content_map = {}

        # Merge vector rankings
        for rank, row in enumerate(vector_results, 1):
            chunk_id = row[0]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (self.rrf_constant + rank))
            content_map[chunk_id] = row[5]  # content

        # Merge FTS rankings
        for rank, row in enumerate(fts_results, 1):
            chunk_id = row[0]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (self.rrf_constant + rank))
            content_map[chunk_id] = row[5]  # content

        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [content_map[cid] for cid in sorted_ids[:self.top_k]]
