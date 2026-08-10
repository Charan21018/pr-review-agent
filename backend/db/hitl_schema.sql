CREATE TABLE IF NOT EXISTS hitl_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL,
    decision TEXT CHECK(decision IN ('APPROVE','REJECT')) NOT NULL,
    reviewer TEXT,
    comments TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
