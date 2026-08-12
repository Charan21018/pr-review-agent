from dotenv import load_dotenv

# Must run before any backend module is imported: backend.db.session reads
# TIGER_DATABASE_URL at module import time (via the hitl_endpoints import
# below), so the shell's environment is not enough on its own.
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .webhook import router as webhook_router
from backend.api.hitl_endpoints import router as hitl_router
from backend.api.economics_endpoints import router as economics_router
from backend.api.reviews_endpoints import router as reviews_router
from backend.queue_enqueuer import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the shared ARQ Redis pool on startup; close it on shutdown."""
    try:
        await init_pool()
    except Exception as e:
        print(f"[Warning] Failed to initialize Redis pool: {e}")
    yield
    try:
        await close_pool()
    except Exception as e:
        print(f"[Warning] Failed to close Redis pool: {e}")


app = FastAPI(title="AI PR Review Agent", lifespan=lifespan)

# Enable CORS for Next.js frontend local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/github")
app.include_router(hitl_router)
app.include_router(economics_router)
app.include_router(reviews_router)
