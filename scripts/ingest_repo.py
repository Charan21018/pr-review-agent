"""
scripts/ingest_repo.py — Ingest a repository codebase into Tiger Memory Store.

Usage:
  python scripts/ingest_repo.py --repo .
"""

import argparse
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.memory.ingestion import CodeIngestor
from backend.memory.tiger_client import TigerMemoryClient

# Shared global instance for local script demos
global_memory_client = TigerMemoryClient()


def main():
    parser = argparse.ArgumentParser(description="Ingest codebase into memory store.")
    parser.add_argument("--repo", default=".", help="Path to repository root")
    args = parser.parse_args()

    ingestor = CodeIngestor(global_memory_client)
    count = ingestor.ingest_directory(args.repo, repo="ai-pr-review-agent")
    print(f"[OK] Ingested {count} code chunks from '{args.repo}' into Tiger Memory Store.")


if __name__ == "__main__":
    main()
