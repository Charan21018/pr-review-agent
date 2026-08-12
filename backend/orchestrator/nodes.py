import asyncio
import os
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime

from backend.orchestrator.state import ReviewState
from backend.memory.context_retriever import ContextRetriever
from backend.agents.security import SecurityAgent
from backend.agents.quality import QualityAgent
from backend.agents.tests import TestsAgent
from backend.agents.docs import DocsAgent
from backend.agents.aggregator import Aggregator
from backend.agents.schemas import Finding, SeverityEnum
from backend.observability.events import event_tracker
from backend.tools.llm_client import chat_completion
from backend.tools.model_router import get_model_for_agent
from backend.api.github_client import GitHubClient

# DB imports
import asyncpg


async def _get_db_conn() -> asyncpg.Connection:
    url = os.getenv("TIGER_DATABASE_URL", "")
    if "ssl=" in url:
        import urllib.parse as up
        parts = list(up.urlparse(url))
        q = dict(up.parse_qsl(parts[4]))
        q.pop("ssl", None)
        parts[4] = up.urlencode(q)
        url = up.urlunparse(parts)
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url, ssl=True)


async def retrieve_context_node(state: ReviewState) -> Dict[str, Any]:
    """Retrieve grounded codebase context via pgvector hybrid search."""
    review_id = uuid.UUID(state["review_id"])
    span_id = uuid.uuid4()
    await event_tracker.track_span_start(review_id, "retriever", span_id, payload={"repo": state["repo"]})

    t0 = asyncio.get_event_loop().time()
    retriever = ContextRetriever(top_k=6)
    chunks = await retriever.retrieve_context(state["pr_diff"], repo=state["repo"])
    duration_ms = int((asyncio.get_event_loop().time() - t0) * 1000)

    await event_tracker.track_span_end(
        review_id, "retriever", span_id, duration_ms, outcome="success",
        payload={"chunks_count": len(chunks)}
    )

    return {"context_chunks": chunks}


async def run_specialists_node(state: ReviewState) -> Dict[str, Any]:
    """Run all four specialist agents in parallel over the diff and context chunks."""
    review_id = uuid.UUID(state["review_id"])
    span_id = uuid.uuid4()
    await event_tracker.track_span_start(review_id, "specialists_orchestrator", span_id)

    t0 = asyncio.get_event_loop().time()

    specialists = [
        SecurityAgent(),
        QualityAgent(),
        TestsAgent(),
        DocsAgent(),
    ]

    # Parallel fan-out
    tasks = [agent.run_with_timeout(state["pr_diff"], state["context_chunks"]) for agent in specialists]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    findings_list: List[Finding] = []
    for agent, result in zip(specialists, results):
        if isinstance(result, list):
            findings_list.extend(result)
            # Log event for each agent's completion
            await event_tracker.track_span_end(
                review_id, agent.name, uuid.uuid4(), 0, outcome="success",
                payload={"findings_count": len(result)}
            )
            # Record the LLM call's cost/token usage (falls back skipped it —
            # last_call_meta stays None on a mock-fallback path with no
            # agent_name, but every real specialist call sets it).
            meta = agent.last_call_meta
            if meta:
                await event_tracker.track_llm_call(
                    review_id, agent.name, uuid.uuid4(),
                    model=meta.get("model", "unknown"),
                    tokens_in=meta.get("tokens_in", 0),
                    tokens_out=meta.get("tokens_out", 0),
                    cost_usd=meta.get("cost_usd", 0.0),
                    latency_ms=meta.get("latency_ms", 0),
                )
        else:
            print(f"[Warning] Agent {agent.name} failed or timed out: {result}")
            await event_tracker.track_span_end(
                review_id, agent.name, uuid.uuid4(), 0, outcome="failed",
                payload={"error": str(result)}
            )

    duration_ms = int((asyncio.get_event_loop().time() - t0) * 1000)
    await event_tracker.track_span_end(review_id, "specialists_orchestrator", span_id, duration_ms, outcome="success")

    # Serialize findings to standard dictionaries for JSON compatibility in state
    serialized_findings = [f.model_dump() for f in findings_list]

    return {"findings": serialized_findings}


async def aggregate_findings_node(state: ReviewState) -> Dict[str, Any]:
    """Deduplicate findings, compute confidence and compile markdown review comment using LLM."""
    review_id = uuid.UUID(state["review_id"])
    span_id = uuid.uuid4()
    await event_tracker.track_span_start(review_id, "aggregator", span_id)

    t0 = asyncio.get_event_loop().time()

    # Convert dictionaries back to Finding objects for the aggregator
    findings_objs = []
    for f in state["findings"]:
        try:
            findings_objs.append(Finding(**f))
        except Exception:
            pass

    aggregator = Aggregator(specialists=[])
    deduped_findings = aggregator._deduplicate_findings(findings_objs)

    # Compute confidence
    if deduped_findings:
        overall_confidence = round(sum(f.confidence for f in deduped_findings) / len(deduped_findings), 3)
    else:
        overall_confidence = 1.0

    # Severity checks
    has_critical = any(f.severity == SeverityEnum.CRITICAL for f in deduped_findings)
    has_high = any(f.severity == SeverityEnum.HIGH for f in deduped_findings)

    if has_critical or overall_confidence < 0.70:
        recommendation = "ESCALATE_TO_HUMAN"
    elif has_high:
        recommendation = "REQUEST_CHANGES"
    else:
        recommendation = "APPROVE"

    # Use LLM to generate the final review summary
    findings_json = json.dumps([f.model_dump() for f in deduped_findings], indent=2)
    system_prompt = """You are a senior software engineering leader summarizing PR reviews.
Generate a structured, helpful PR comment in Markdown. Group findings by severity (Critical, High, Medium, Low).
Add a clear final recommendation: APPROVE, REQUEST_CHANGES, or ESCALATE_TO_HUMAN."""
    
    user_prompt = f"""
    PR: {state['repo']}#{state['pr_number']}
    Findings: {findings_json}
    Overall Confidence: {overall_confidence}
    Recommendation: {recommendation}
    """

    cost_usd = 0.0
    tokens_in = 0
    tokens_out = 0
    try:
        completion = await chat_completion(
            model=get_model_for_agent("orchestrator"),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            agent_name="orchestrator",
        )
        summary = completion["text"]
        cost_usd = completion["cost_usd"]
        tokens_in = completion["tokens_in"]
        tokens_out = completion["tokens_out"]
        await event_tracker.track_llm_call(
            review_id, "aggregator", span_id,
            model=completion.get("model", "unknown"),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=completion.get("latency_ms", 0),
        )
    except Exception as e:
        summary = f"Review completed with {len(deduped_findings)} findings. Recommendation: {recommendation}."

    duration_ms = int((asyncio.get_event_loop().time() - t0) * 1000)
    await event_tracker.track_span_end(
        review_id, "aggregator", span_id, duration_ms, outcome="success",
        confidence=overall_confidence
    )

    # Persist the review and findings to the PostgreSQL database!
    conn = await _get_db_conn()
    try:
        # 1. Insert pr_review_records. review_id is the GitHub delivery_id, so a
        # redelivered webhook (same id) must be a harmless no-op here, matching
        # the idempotency invariant the webhook layer already assumes (M1).
        inserted = await conn.fetchrow(
            """
            INSERT INTO pr_review_records (id, repo, pr_number, created_at, status, summary, total_cost_usd, total_tokens)
            VALUES ($1, $2, $3, now(), $4, $5, $6, $7)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            review_id,
            state["repo"],
            state["pr_number"],
            recommendation.lower(),
            summary,
            cost_usd,
            tokens_in + tokens_out
        )
        if inserted is None:
            print(f"[Info] Review {review_id} already persisted (duplicate delivery) — skipping finding inserts.")
            return {
                "recommendation": recommendation,
                "overall_confidence": overall_confidence,
                "summary": summary,
                "has_critical": has_critical,
                "cost_usd": cost_usd,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": duration_ms,
            }

        # 2. Insert individual finding_records
        for f in deduped_findings:
            finding_uuid = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO finding_records (id, review_id, file_path, line_start, line_end, symbol, severity, description, confidence, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, now())
                """,
                finding_uuid,
                review_id,
                f.file_path,
                f.line_start,
                f.line_end,
                f.symbol if hasattr(f, 'symbol') else None,
                f.severity.value,
                f.rationale,
                f.confidence
            )

            # If it's escalated, write to hitl_reviews queue
            if recommendation == "ESCALATE_TO_HUMAN":
                await conn.execute(
                    """
                    INSERT INTO hitl_reviews (id, finding_id, assigned_to, status, decision, reviewer_comments, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, now())
                    """,
                    uuid.uuid4(),
                    finding_uuid,
                    None,
                    "pending",
                    None,
                    None
                )
    except Exception as e:
        print(f"[Error] Failed to persist review records to Postgres: {e}")
    finally:
        await conn.close()

    return {
        "recommendation": recommendation,
        "overall_confidence": overall_confidence,
        "summary": summary,
        "has_critical": has_critical,
        "cost_usd": cost_usd,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": duration_ms
    }


async def hitl_gate_node(state: ReviewState) -> Dict[str, Any]:
    """Execute HITL check. If ESCALATE_TO_HUMAN, transition to PENDING. Otherwise NONE."""
    if state["recommendation"] == "ESCALATE_TO_HUMAN":
        return {"hitl_action": "PENDING"}
    return {"hitl_action": "NONE"}


async def post_results_node(state: ReviewState) -> Dict[str, Any]:
    """Post final review comments to GitHub (unless HITL is pending)."""
    if state["hitl_action"] == "PENDING":
        # Don't comment on GitHub yet; wait for human approval/rejection
        print(f"[HITL] Review {state['review_id']} escalated to human. Postponing GitHub comment.")
        return {}

    # Otherwise post to GitHub
    token = os.getenv("GITHUB_TOKEN")
    if token and not token.startswith("ghp_XXX") and not token.startswith("github_pat_YOUR"):
        try:
            gh = GitHubClient(token)
            posted = gh.post_review(
                repo_full_name=state["repo"],
                pull_number=state["pr_number"],
                body=state["summary"],
                decision=state["recommendation"]
            )
            if posted:
                print("[GitHub] Posted review comment successfully.")
            else:
                print(f"[GitHub] Review NOT posted for PR {state['pr_number']} — see the [DLQ] line above for the reason (commonly a token permissions issue).")
        except Exception as e:
            print(f"[Error] Failed to post review to GitHub: {e}")
    else:
        print(f"[Mock GitHub] Review results:\n{state['summary']}")

    return {}
