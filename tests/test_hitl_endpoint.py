import os
import sqlite3
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.hitl import router as hitl_router
from backend.api.__init__ import *  # ensures migration runs

app = FastAPI()
app.include_router(hitl_router)
client = TestClient(app)

def test_hitl_endpoint_creates_row(tmp_path, monkeypatch):
    # Use temporary database
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", str(db_path))
    # Ensure migration runs
    import importlib
    import backend.api.__init__ as api_init
    importlib.reload(api_init)
    payload = {
        "review_id": "rev-123",
        "decision": "APPROVE",
        "reviewer": "alice",
        "comments": "Looks good"
    }
    response = client.post("/hitl", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "recorded"
    # Verify DB row
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT review_id, decision, reviewer, comments FROM hitl_events WHERE review_id = ?",
                        (payload["review_id"],)).fetchone()
    conn.close()
    assert row == (payload["review_id"], payload["decision"], payload["reviewer"], payload["comments"])
