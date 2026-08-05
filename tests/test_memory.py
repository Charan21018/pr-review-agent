"""
tests/test_memory.py — Acceptance tests for Tiger Memory Store & Code Ingestion.

Covers:
  - CodeIngestor: symbol-aware chunking of source files
  - TigerMemoryClient: hybrid vector + keyword search with RRF scoring
  - Specialist Grounding: verifying context_chunks are reflected in Finding rationales
"""

import pytest

from backend.agents.security import SecurityAgent
from backend.memory.ingestion import CodeIngestor
from backend.memory.tiger_client import TigerMemoryClient


class TestCodeIngestor:

    def test_chunk_file(self, tmp_path):
        sample_file = tmp_path / "service.py"
        sample_file.write_text(
            "def calculate_total(price, tax):\n"
            "    return price + tax\n\n"
            "class PaymentProcessor:\n"
            "    def process(self):\n"
            "        pass\n",
            encoding="utf-8",
        )

        client = TigerMemoryClient()
        ingestor = CodeIngestor(client)
        chunks = ingestor.chunk_file(str(sample_file))

        assert len(chunks) >= 2
        symbols = [c["symbol"] for c in chunks if c["symbol"]]
        assert "calculate_total" in symbols or "PaymentProcessor" in symbols


class TestTigerMemoryClient:

    def test_hybrid_retrieval(self):
        client = TigerMemoryClient()
        client.add_chunk("c1", "repo", "auth/jwt.py", "verify_token", "def verify_token(token): authenticate user")
        client.add_chunk("c2", "repo", "db/conn.py", "get_connection", "def get_connection(): connect postgres database")
        client.add_chunk("c3", "repo", "api/routes.py", "login", "def login(): handle user authentication endpoint")

        results = client.retrieve("user authentication token", top_k=2)

        assert len(results) == 2
        paths = [r.path for r in results]
        assert "auth/jwt.py" in paths or "api/routes.py" in paths
        assert results[0].score > 0.0

    async def test_specialist_grounding(self):
        client = TigerMemoryClient()
        client.add_chunk("c1", "repo", "security.py", "check", "def check_key(): pass")

        chunks = [c.content for c in client.retrieve("check_key")]

        agent = SecurityAgent()
        diff = "+ api_key = \"secret_key_12345678\""
        findings = await agent.run_with_timeout(diff, context_chunks=chunks)

        assert len(findings) >= 1
        assert "Grounded in" in findings[0].rationale
