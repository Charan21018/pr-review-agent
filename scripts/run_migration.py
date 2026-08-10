import sqlite3
import os

def run_migration(db_path: str, sql_path: str):
    if not os.path.exists(sql_path):
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    conn = sqlite3.connect(db_path)
    try:
        with open(sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        conn.executescript(sql)
        conn.commit()
        print("Migration applied successfully.")
    finally:
        conn.close()

if __name__ == "__main__":
    db = os.getenv("DATABASE_URL", "database.db")
    sql_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "db", "hitl_schema.sql"))
    print(f"Running migration using schema: {sql_file}")
    run_migration(db, sql_file)
