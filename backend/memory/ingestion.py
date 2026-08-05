"""
backend/memory/ingestion.py — Code Chunking & Repository Ingestion Pipeline.

Chunks source code files by symbol definitions (def/class) or block boundaries
and loads them into TigerMemoryClient.
"""

import os
import re
from pathlib import Path
from typing import List, Optional

from backend.memory.tiger_client import TigerMemoryClient


class CodeIngestor:

    SUPPORTED_EXTENSIONS = {".py", ".ts", ".js", ".html", ".md", ".sql", ".ini"}

    def __init__(self, memory_client: TigerMemoryClient):
        self.client = memory_client

    def chunk_file(self, file_path: str, repo: str = "local/repo") -> List[dict]:
        """Chunk a single file into symbol-aware blocks."""
        path_obj = Path(file_path)
        if path_obj.suffix not in self.SUPPORTED_EXTENSIONS:
            return []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        lines = content.splitlines()
        chunks: List[dict] = []
        current_chunk: List[str] = []
        current_symbol: Optional[str] = None
        chunk_idx = 0

        for line in lines:
            # Symbol detection (Python def/class or JS function/class)
            symbol_match = re.search(r'^\s*(def|class|function|async def)\s+([a-zA-Z0-9_]+)', line)
            if symbol_match:
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(
                            {
                                "chunk_id": f"{file_path}#{chunk_idx}",
                                "repo": repo,
                                "path": file_path,
                                "symbol": current_symbol,
                                "content": chunk_text,
                            }
                        )
                        chunk_idx += 1
                    current_chunk = []
                current_symbol = symbol_match.group(2)

            current_chunk.append(line)

            # Cap chunk length at ~40 lines if no new symbol appears
            if len(current_chunk) >= 40:
                chunk_text = "\n".join(current_chunk).strip()
                if chunk_text:
                    chunks.append(
                        {
                            "chunk_id": f"{file_path}#{chunk_idx}",
                            "repo": repo,
                            "path": file_path,
                            "symbol": current_symbol,
                            "content": chunk_text,
                        }
                    )
                    chunk_idx += 1
                current_chunk = []
                current_symbol = None

        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                chunks.append(
                    {
                        "chunk_id": f"{file_path}#{chunk_idx}",
                        "repo": repo,
                        "path": file_path,
                        "symbol": current_symbol,
                        "content": chunk_text,
                    }
                )

        return chunks

    def ingest_directory(self, root_dir: str, repo: str = "local/repo") -> int:
        """Walk a directory, chunk all supported code files, and load into memory client."""
        total_chunks = 0
        for root, dirs, files in os.walk(root_dir):
            # Skip hidden, virtualenv, and build dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", "venv", "env")]

            for file_name in files:
                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, root_dir)
                file_chunks = self.chunk_file(full_path, repo=repo)

                for chunk in file_chunks:
                    self.client.add_chunk(
                        chunk_id=chunk["chunk_id"],
                        repo=repo,
                        path=rel_path,
                        symbol=chunk["symbol"],
                        content=chunk["content"],
                    )
                    total_chunks += 1

        return total_chunks
