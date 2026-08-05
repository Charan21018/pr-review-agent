"""
scripts/dry_run.py — CLI tool to execute the multi-agent PR review pipeline on a diff file.

Usage:
  python scripts/dry_run.py --pr-diff tests/fixtures/sample.diff
"""

import argparse
import asyncio
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.agents.aggregator import Aggregator


async def main():
    parser = argparse.ArgumentParser(description="Run AI PR Review Agent parallel specialists on a diff file.")
    parser.add_argument("--pr-diff", required=True, help="Path to PR diff file")
    args = parser.parse_args()

    try:
        with open(args.pr_diff, "r", encoding="utf-8") as f:
            diff_text = f.read()
    except Exception as e:
        print(f"Error reading diff file {args.pr_diff}: {e}", file=sys.stderr)
        sys.exit(1)

    aggregator = Aggregator()
    review = await aggregator.run_review(diff_text)

    # Convert to dictionary and print as indented JSON
    output = review.model_dump()
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
