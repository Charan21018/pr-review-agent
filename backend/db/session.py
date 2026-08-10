from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("TIGER_DATABASE_URL") or os.getenv("POSTGRES_URL") or "postgresql+asyncpg://postgres:postgres@localhost/pr_review"
if "postgresql://" in DATABASE_URL and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Async engine for asyncpg driver
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Session factory
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """Provide a transactional async session.
    Usage::
        async with get_db() as db:
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session
