import asyncio
import os
import sys
import asyncpg
from dotenv import load_dotenv

# Load env file
load_dotenv()

DATABASE_URL = os.getenv("TIGER_DATABASE_URL")
if not DATABASE_URL:
    print("Error: TIGER_DATABASE_URL environment variable is not set.")
    sys.exit(1)

# Convert postgresql+asyncpg:// to postgresql:// for asyncpg connection
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

# Handle SSL mode for asyncpg
ssl_mode = True
if "ssl=" in DATABASE_URL:
    import urllib.parse as urlparse
    url_parts = list(urlparse.urlparse(DATABASE_URL))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    if 'ssl' in query:
        del query['ssl']
    url_parts[4] = urlparse.urlencode(query)
    DATABASE_URL = urlparse.urlunparse(url_parts)

MIGRATIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "migrations"))

async def run_migrations():
    print(f"Connecting to database to run migrations...")
    try:
        conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_mode)
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)

    print("Successfully connected to database.")

    # Get migration files in order
    migration_files = sorted(
        [f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")]
    )

    for migration_file in migration_files:
        migration_path = os.path.join(MIGRATIONS_DIR, migration_file)
        print(f"Applying migration: {migration_file}...")
        try:
            with open(migration_path, "r", encoding="utf-8") as f:
                sql = f.read()
            
            # Execute SQL commands. Since some statements might be complex,
            # execute them inside a transaction.
            async with conn.transaction():
                await conn.execute(sql)
            print(f"[OK] Applied {migration_file} successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to apply {migration_file}: {e}")
            await conn.close()
            sys.exit(1)

    await conn.close()
    print("All migrations applied successfully.")

if __name__ == "__main__":
    asyncio.run(run_migrations())
