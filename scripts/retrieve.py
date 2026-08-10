"""
scripts/retrieve.py — Query Tiger Memory Store using hybrid RRF search.

Usage:
  python scripts/retrieve.py --query "authentication middleware" --top-k 5
"""
import argparse
import asyncio
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.memory.context_retriever import ContextRetriever
from backend.memory.tiger_client import search_chunks
from backend.memory.embedder import embed_text


async def async_main():
    parser = argparse.ArgumentParser(description="Query Tiger Memory Store using hybrid search.")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    args = parser.parse_args()

    # 1. Embed query
    print(f"Embedding query: '{args.query}'...")
    query_embedding = await embed_text(args.query)

    # 2. Retrieve chunks using the database hybrid search function
    print("Performing hybrid vector+FTS search...")
    results = await search_chunks(query_embedding, top_k=args.top_k)

    print(f"\n=== Hybrid Retrieval Results for '{args.query}' (top {len(results)}) ===")
    for idx, res in enumerate(results, 1):
        # Result tuple: (id, repo, path, symbol, chunk_index, content, score)
        chunk_id, repo, path, symbol, chunk_index, content, score = res
        print(f"\n[{idx}] Score (RRF): {score:.4f} | Path: {path} | Symbol: {symbol or 'N/A'}")
        preview = content.replace("\n", " ")[:120]
        print(f"    Content: {preview}...")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
