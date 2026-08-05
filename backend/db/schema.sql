-- schema.sql — Tiger Cloud (TimescaleDB / pgvector / pgvectorscale)
-- Run once against your Tiger Cloud instance before starting the worker.
-- Prereqs: pgvector, pgvectorscale (TimescaleDB extensions — enabled by default on Tiger Cloud).

-- ── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;           -- pgvector: VECTOR type + cosine ops
CREATE EXTENSION IF NOT EXISTS vectorscale;      -- pgvectorscale: DiskANN index

-- ── Lane 1: Memory — code_chunks ────────────────────────────────────────────
-- Stores embedded code chunks for hybrid retrieval (cosine + FTS).
-- Populated by scripts/ingest_repo.py (M3).
CREATE TABLE IF NOT EXISTS code_chunks (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    repo         TEXT         NOT NULL,
    path         TEXT         NOT NULL,
    symbol       TEXT,                           -- function/class name (nullable)
    chunk_index  INT          NOT NULL,          -- order within file
    content      TEXT         NOT NULL,
    embedding    VECTOR(256)  NOT NULL,          -- text-embedding-3-large, 256 dims
    token_count  INT,
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- DiskANN index: fast ANN search over millions of chunks without RAM blowout
CREATE INDEX IF NOT EXISTS code_chunks_emb_idx
    ON code_chunks USING diskann (embedding vector_cosine_ops);

-- Full-text search column for exact symbol / identifier matches
ALTER TABLE code_chunks
    ADD COLUMN IF NOT EXISTS content_tsv TSVECTOR
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX IF NOT EXISTS code_chunks_fts_idx
    ON code_chunks USING GIN (content_tsv);

-- ── Lane 2: Truth — reviews + findings ──────────────────────────────────────
-- Durable record of every review decision and its findings.
CREATE TABLE IF NOT EXISTS reviews (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    github_delivery  TEXT         UNIQUE NOT NULL,   -- X-GitHub-Delivery for dedup
    repo             TEXT         NOT NULL,
    pr_number        INT          NOT NULL,
    head_sha         TEXT         NOT NULL,
    status           TEXT         NOT NULL DEFAULT 'pending',  -- pending|posted|queued_hitl|failed
    overall_confidence  NUMERIC(4,3),
    github_review_id    BIGINT,                       -- set after GitHub API post
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS findings (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id    UUID         NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    specialist   TEXT         NOT NULL,   -- security|quality|tests|docs
    severity     TEXT         NOT NULL,   -- CRITICAL|HIGH|MEDIUM|LOW|INFO
    category     TEXT         NOT NULL,
    file_path    TEXT,
    line_start   INT,
    line_end     INT,
    rationale    TEXT         NOT NULL,
    confidence   NUMERIC(4,3) NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS findings_review_idx ON findings(review_id);
CREATE INDEX IF NOT EXISTS findings_severity_idx ON findings(severity);

-- ── Lane 3: Time — agent_events (hypertable) ─────────────────────────────────
-- Every agent action: span start/end, LLM call, tool call, decision, escalation.
-- This is I3's single source of truth for cost, latency, and decisions.
CREATE TABLE IF NOT EXISTS agent_events (
    ts            TIMESTAMPTZ  NOT NULL,
    review_id     UUID         NOT NULL,
    agent         TEXT         NOT NULL,   -- security|quality|tests|docs|aggregator|webhook
    span_id       UUID         NOT NULL DEFAULT gen_random_uuid(),
    parent_span   UUID,
    event_type    TEXT         NOT NULL,   -- span.start|span.end|llm.call|tool.call|decision|escalation
    model         TEXT,
    tokens_in     INT,
    tokens_out    INT,
    cost_usd      NUMERIC(10,6),           -- I3: non-null on llm.call rows
    latency_ms    INT,                     -- I3: non-null on span.end rows
    outcome       TEXT,                    -- approved|request_changes|critical_block|escalated
    confidence    NUMERIC(4,3),
    payload       JSONB
);

-- Convert to hypertable partitioned by day (TimescaleDB)
SELECT create_hypertable(
    'agent_events',
    by_range('ts', INTERVAL '1 day'),
    if_not_exists => TRUE
);

-- ── Continuous aggregates (dashboard rollups) ─────────────────────────────────
-- agent_health_1m: cost + latency + rejection rate per agent per minute
CREATE MATERIALIZED VIEW IF NOT EXISTS agent_health_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts)                           AS bucket,
    agent,
    count(*) FILTER (WHERE event_type = 'llm.call')       AS llm_calls,
    sum(cost_usd)                                         AS cost_usd,
    approx_percentile(0.95, percentile_agg(latency_ms))   AS p95_ms,
    count(*) FILTER (WHERE outcome = 'escalated')::float
        / NULLIF(count(*) FILTER (WHERE outcome IS NOT NULL), 0) AS escalation_rate
FROM agent_events
GROUP BY bucket, agent
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'agent_health_1m',
    start_offset  => INTERVAL '2 hours',
    end_offset    => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);
