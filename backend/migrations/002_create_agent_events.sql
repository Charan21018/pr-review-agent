-- Migration: create_agent_events table with TimescaleDB hypertable
-- Requires TimescaleDB extension to be installed.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS agent_events (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    review_id UUID NOT NULL,
    agent TEXT NOT NULL,
    event_type TEXT NOT NULL,
    span_id UUID NOT NULL,
    parent_span UUID,
    model TEXT,
    tokens_in INT,
    tokens_out INT,
    cost_usd FLOAT,
    latency_ms INT,
    outcome TEXT,
    confidence FLOAT,
    payload JSONB,
    PRIMARY KEY (id, ts)
);

-- Convert to hypertable for efficient time-series queries
SELECT create_hypertable('agent_events', 'ts', if_not_exists => TRUE);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_agent_events_review_id ON agent_events (review_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_agent ON agent_events (agent);
CREATE INDEX IF NOT EXISTS idx_agent_events_event_type ON agent_events (event_type);
