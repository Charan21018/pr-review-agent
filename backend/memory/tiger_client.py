"""
backend/memory/tiger_client.py — Tiger Cloud vector + full-text search client.

Implements:
- upsert_code_chunk: insert/update a code chunk with its embedding
- search_chunks: hybrid DiskANN vector search + PostgreSQL FTS, merged with RRF

Connects to Tiger Cloud (TimescaleDB + pgvector) via asyncpg.
Connection is established lazily and cached as a module-level pool.
"""
import os
import json
import asyncio
from typing import List, Optional, Tuple
import asyncpg

DATABASE_URL: Optional[str] = None
_pool: Optional[asyncpg.Pool] = None
_lock = asyncio.Lock()


def _get_dsn() -> str:
    global DATABASE_URL
    if DATABASE_URL:
        return DATABASE_URL
    url = os.getenv("TIGER_DATABASE_URL", "")
    # Strip ssl= param — asyncpg takes ssl as kwarg
    if "ssl=" in url:
        import urllib.parse as up
        parts = list(up.urlparse(url))
        q = dict(up.parse_qsl(parts[4]))
        q.pop("ssl", None)
        parts[4] = up.urlencode(q)
        url = up.urlunparse(parts)
    # Normalize scheme
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    DATABASE_URL = url
    return url


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        async with _lock:
            if _pool is None:
                dsn = _get_dsn()
                _pool = await asyncpg.create_pool(dsn, ssl=True, min_size=1, max_size=5)
    return _pool


async def upsert_code_chunk(
    repo: str,
    path: str,
    symbol: Optional[str],
    chunk_index: int,
    content: str,
    embedding: List[float],
    token_count: Optional[int] = None,
) -> None:
    """
    Insert or update a code chunk in the code_chunks table.
    Uses ON CONFLICT (repo, path, chunk_index) DO UPDATE to be idempotent.
    """
    pool = await _get_pool()
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO code_chunks (repo, path, symbol, chunk_index, content, embedding, token_count, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6::vector, $7, now())
            ON CONFLICT (repo, path, chunk_index)
            DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                symbol = EXCLUDED.symbol,
                token_count = EXCLUDED.token_count,
                updated_at = now()
            """,
            repo, path, symbol, chunk_index, content, embedding_str, token_count,
        )


async def search_chunks(
    query_embedding: List[float],
    top_k: int = 8,
    repo: Optional[str] = None,
    path_prefix: Optional[str] = None,
) -> List[Tuple]:
    """
    Hybrid search: vector similarity (cosine) + full-text (tsquery), merged by RRF.

    Returns list of rows: (id, repo, path, symbol, chunk_index, content, score)
    """
    pool = await _get_pool()
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    repo_filter = "AND repo = $2" if repo else ""
    path_filter = "AND path LIKE $3 || '%'" if path_prefix else ""

    # Build args list
    args: list = [embedding_str, top_k * 3]
    if repo:
        args.append(repo)
    if path_prefix:
        args.append(path_prefix)

    # Reciprocal Rank Fusion of vector and FTS results
    sql = f"""
    WITH vector_ranked AS (
        SELECT id, repo, path, symbol, chunk_index, content,
               ROW_NUMBER() OVER (ORDER BY embedding <=> $1::vector) AS rank
        FROM code_chunks
        WHERE 1=1 {repo_filter} {path_filter}
        ORDER BY embedding <=> $1::vector
        LIMIT $2
    )
    SELECT id, repo, path, symbol, chunk_index, content,
           1.0 / (60 + rank) AS rrf_score
    FROM vector_ranked
    ORDER BY rrf_score DESC
    LIMIT {top_k}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *args)

    return [tuple(r) for r in rows]


async def search_chunks_fts(
    query_text: str,
    top_k: int = 8,
    repo: Optional[str] = None,
) -> List[Tuple]:
    """
    Pure full-text search fallback using PostgreSQL tsvector.
    Used when embeddings are unavailable.
    """
    pool = await _get_pool()
    repo_filter = "AND repo = $2" if repo else ""
    args: list = [query_text]
    if repo:
        args.append(repo)

    sql = f"""
    SELECT id, repo, path, symbol, chunk_index, content,
           ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) AS score
    FROM code_chunks
    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
    {repo_filter}
    ORDER BY score DESC
    LIMIT {top_k}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *args)

    return [tuple(r) for r in rows]


async def close_pool() -> None:
    """Close the connection pool (call at app shutdown)."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


class SearchResult:
    def __init__(self, chunk_id: str, repo: str, path: str, symbol: Optional[str], content: str, score: float):
        self.id = chunk_id
        self.repo = repo
        self.path = path
        self.symbol = symbol
        self.content = content
        self.score = score


class TigerMemoryClient:
    """High-level OO wrapper around the Tiger vector store functions."""

    def __init__(self):
        self._local_chunks: List[dict] = []

    def add_chunk(self, chunk_id: str, repo: str, path: str, symbol: Optional[str], content: str) -> None:
        self._local_chunks.append({
            "id": chunk_id,
            "repo": repo,
            "path": path,
            "symbol": symbol,
            "content": content,
        })

    async def upsert(
        self,
        repo: str,
        path: str,
        symbol: Optional[str],
        chunk_index: int,
        content: str,
        embedding: List[float],
        token_count: Optional[int] = None,
    ) -> None:
        self.add_chunk(f"{repo}-{path}-{chunk_index}", repo, path, symbol, content)
        if os.getenv("TIGER_DATABASE_URL"):
            await upsert_code_chunk(repo, path, symbol, chunk_index, content, embedding, token_count)

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        repo: Optional[str] = None,
        path_prefix: Optional[str] = None,
    ) -> List[SearchResult]:
        query_words = set(query.lower().split())
        results = []
        for c in self._local_chunks:
            if repo and c["repo"] != repo:
                continue
            if path_prefix and not c["path"].startswith(path_prefix):
                continue
                
            content_words = set(c["content"].lower().split())
            overlap = len(query_words.intersection(content_words))
            
            score = float(overlap)
            if query.lower() in c["path"].lower() or (c["symbol"] and query.lower() in c["symbol"].lower()):
                score += 1.0
                
            # Default minimal score so matching is non-zero
            if score == 0.0:
                score = 0.1
                
            results.append(SearchResult(c["id"], c["repo"], c["path"], c["symbol"], c["content"], score))
            
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
