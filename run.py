"""
run.py  –  Custom uvicorn entry point for Windows.

Sets WindowsSelectorEventLoopPolicy BEFORE uvicorn creates its event loop so
that redis.asyncio (used by ARQ) can connect on Windows with Python 3.8+.
"""
import sys
import asyncio

# Must be set before any asyncio event loop is created.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
