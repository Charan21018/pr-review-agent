"""
scripts/retrieve.py — Query Tiger Memory Store using hybrid RRF search.

Usage:
  python scripts/retrieve.py --query "authentication middleware" --top-k 5
"""

import argparse
import json
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.memory.ingestion import CodeIngestor
from backend.memory.tiger_client import TigerMemoryClient


def main():
    parser = argparse.ArgumentParser(description="Query Tiger Memory Store using hybrid search.")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--repo-path", default=".", help="Path to repo for instant demo context")
    args = parser.parse_args()

    client = TigerMemoryClient()
    ingestor = CodeIngestor(client)
    ingestor.ingest_directory(args.repo_path, repo="ai-pr-review-agent")

    results = client.retrieve(args.query, top_k=args.top_k)

    print(f"=== Hybrid Retrieval Results for '{args.query}' (top {len(results)}) ===")
    for idx, res in enumerate(results, 1):
        print(f"\n[{idx}] Score: {res.score:.4f} | Path: {res.path} | Symbol: {res.symbol or 'N/A'}")
        preview = res.content.replace("\n", " ")[:120]
        print(f"    Content: {preview}...")


if __name__ == "__main__":
    main()
