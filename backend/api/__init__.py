import os
import sqlite3

# Run migration for hitl_events if not present
_schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "hitl_schema.sql")
_db_path = os.getenv("DATABASE_URL", "database.db")
if os.path.exists(_schema_path):
    conn = sqlite3.connect(_db_path)
    with open(_schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()
