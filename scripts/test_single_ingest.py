import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.memory.ingestion import CodeIngestor
from backend.memory.tiger_client import TigerMemoryClient

async def test():
    print("Initializing TigerMemoryClient...")
    client = TigerMemoryClient()
    
    print("Initializing CodeIngestor...")
    ingestor = CodeIngestor(client)
    
    test_file = "backend/settings.py"
    print(f"Ingesting single file: {test_file}...")
    
    try:
        chunks = await ingestor.ingest_file(test_file, repo="ai-pr-review-agent", path="backend/settings.py")
        print(f"Ingested successfully: {chunks} chunk(s).")
    except Exception as e:
        print(f"Ingestion failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
