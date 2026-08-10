import os
from pathlib import Path
import numpy as np
from typing import List, Optional

from backend.memory.tiger_client import upsert_code_chunk, TigerMemoryClient
from backend.memory.embedder import embed_text


class CodeIngestor:
    """Utility to ingest source files into the Tiger vector store.

    Example usage::
        client = TigerMemoryClient()
        ingestor = CodeIngestor(client)
        await ingestor.ingest_directory("/path/to/repo", repo="owner/name")
    """

    def __init__(self, client: Optional[TigerMemoryClient] = None):
        self.client = client or TigerMemoryClient()

    def chunk_file(self, file_path: str) -> List[dict]:
        """Parses a file and extracts chunks based on function/class definitions (AST)."""
        import ast
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            print(f"[Warning] Failed to read {file_path}: {e}")
            return []

        chunks = []
        try:
            tree = ast.parse(code)
            lines = code.splitlines()
            
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start_line = node.lineno - 1
                    end_line = getattr(node, "end_lineno", len(lines))
                    content = "\n".join(lines[start_line:end_line])
                    chunks.append({
                        "symbol": node.name,
                        "content": content,
                        "line_start": node.lineno,
                        "line_end": end_line
                    })
            
            # Fallback if no symbols found
            if not chunks and code.strip():
                chunks.append({
                    "symbol": None,
                    "content": code,
                    "line_start": 1,
                    "line_end": len(lines)
                })
        except Exception as e:
            print(f"[Warning] AST parse failed for {file_path}: {e}")
            lines = code.splitlines()
            chunks.append({
                "symbol": None,
                "content": code,
                "line_start": 1,
                "line_end": len(lines)
            })
            
        return chunks

    async def ingest_file(self, file_path: str, repo: str, path: str, chunk_size: int = 1000) -> int:
        """Read a file, split into chunks, compute embeddings, and upsert.

        Args:
            file_path: Absolute path to the source file.
            repo: Repository identifier (e.g., "owner/name").
            path: Repository‑relative file path used for storage.
            chunk_size: Approximate number of characters per chunk.

        Returns:
            The number of chunks ingested.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"[Warning] Failed to read {file_path}: {e}")
            return 0

        if not content.strip():
            return 0

        # Simple naive chunking – split on character boundaries
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        
        for idx, chunk in enumerate(chunks):
            try:
                embedding = await embed_text(chunk)
                await self.client.upsert(
                    repo=repo,
                    path=path,
                    symbol=None,
                    chunk_index=idx,
                    content=chunk,
                    embedding=embedding,
                    token_count=len(chunk) // 4,  # simple heuristic estimate
                )
            except Exception as e:
                print(f"[Error] Failed to ingest chunk {idx} of {path}: {e}")
                return idx

        return len(chunks)

    async def ingest_directory(self, directory: str, repo: str) -> int:
        """Recursively walk a directory and ingest supported source files.

        Currently ingests files with extensions .py, .js, .ts, .go, .java, .cpp, .c, .rs, .md.
        Returns the total number of chunks ingested.
        """
        supported_exts = {".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".rs", ".md"}
        total_chunks = 0
        for root, _, files in os.walk(directory):
            # Skip hidden folders
            if any(part.startswith('.') for part in Path(root).parts):
                continue
            for fname in files:
                _, ext = os.path.splitext(fname)
                if ext.lower() in supported_exts:
                    full_path = os.path.join(root, fname)
                    # Repository‑relative path (POSIX style for consistency)
                    rel_path = os.path.relpath(full_path, directory).replace(os.sep, "/")
                    chunks_count = await self.ingest_file(full_path, repo=repo, path=rel_path)
                    total_chunks += chunks_count
        return total_chunks
