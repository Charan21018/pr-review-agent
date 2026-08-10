from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, func, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

# ---------------------------------------------------
# Code chunk storage (RAG memory)
# ---------------------------------------------------
class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo = Column(String, nullable=False)
    path = Column(String, nullable=False)
    symbol = Column(String)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # Vector column – pgvector type (VECTOR(256))
    embedding = Column(ARRAY(Float, dimensions=1), nullable=False)
    token_count = Column(Integer)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Unique constraint to allow upserts on same chunk
        # (repo, path, chunk_index) must be unique
        # The actual DDL will add a UNIQUE index.
        {},
    )

# ---------------------------------------------------
# PR Review and HITL models
# ---------------------------------------------------

class PRReviewRecord(Base):
    __tablename__ = "pr_review_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo = Column(String, nullable=False)
    pr_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String, nullable=False)  # pending, completed, escalated
    summary = Column(Text)
    total_cost_usd = Column(Float)
    total_tokens = Column(Integer)

class FindingRecord(Base):
    __tablename__ = "finding_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("pr_review_records.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)
    line_start = Column(Integer)
    line_end = Column(Integer)
    symbol = Column(String)
    severity = Column(String)
    description = Column(Text)
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class HitlReview(Base):
    __tablename__ = "hitl_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("finding_records.id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(String)
    status = Column(String, nullable=False, default="pending")
    decision = Column(String)
    reviewer_comments = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class HitlFeedback(Base):
    __tablename__ = "hitl_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hitl_review_id = Column(UUID(as_uuid=True), ForeignKey("hitl_reviews.id", ondelete="CASCADE"), nullable=False)
    feedback = Column(Text)
    rating = Column(Integer)  # 1-5
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ---------------------------------------------------
# Event spine (observability)
# ---------------------------------------------------
class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    review_id = Column(UUID(as_uuid=True), nullable=False)
    agent = Column(String, nullable=False)
    span_id = Column(UUID(as_uuid=True), nullable=False)
    parent_span = Column(UUID(as_uuid=True))
    event_type = Column(String, nullable=False)  # span.start|span.end|llm.call|tool.call|decision|escalation
    model = Column(String)
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    cost_usd = Column(Float)
    latency_ms = Column(Integer)
    outcome = Column(String)
    confidence = Column(Float)
    payload = Column(JSON)

    # Indexes will be added via migrations (e.g., hypertable on ts)
