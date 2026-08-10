"""
backend/queue/worker.py — ARQ worker definition.

Invokes the LangGraph orchestrator graph to run the PR review pipeline.
"""
import os
import uuid
from typing import Any

from backend.orchestrator.graph import create_review_graph
from backend.api.github_client import GitHubClient

# Stub diff fallback for local verification when GITHUB_TOKEN is missing/placeholder
MOCK_DIFF = """diff --git a/app.py b/app.py
index e69de29..8b13789 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,11 @@
 def main():
+    # CRITICAL: Hardcoded API Key
+    api_key = "sk-proj-supersecretkeyhere"
+    
+    # HIGH: Command Injection
+    import os
+    os.system("ping " + api_key)
+    
+    # LOW: debug print statement
+    print("App started with key: " + api_key)
     pass
"""

async def review_pr(ctx: dict, payload: dict) -> dict:
    """
    Entry point for the async review pipeline.
    Invokes the LangGraph orchestrator flow.
    """
    # X-GitHub-Delivery header (if present) is used to track idempotency/review_id
    delivery_id = payload.get("delivery_id") or str(uuid.uuid4())
    
    pr_number = payload.get("pull_request", {}).get("number", 0)
    repo = payload.get("repository", {}).get("full_name", "unknown/repo")
    
    print(f"[Worker] Starting PR review for {repo}#{pr_number} with Review ID: {delivery_id}")
    
    # 1. Fetch PR Diff
    token = os.getenv("GITHUB_TOKEN")
    pr_diff = ""
    if token and not token.startswith("ghp_XXX") and not token.startswith("github_pat_YOUR"):
        try:
            gh = GitHubClient(token)
            pr_diff = await gh.get_pull_request_diff(repo, pr_number)
            print(f"[Worker] Fetched PR diff ({len(pr_diff)} chars) from GitHub.")
        except Exception as e:
            print(f"[Warning] Failed to fetch diff from GitHub: {e}. Falling back to mock diff.")
            pr_diff = MOCK_DIFF
    else:
        print("[Worker] GITHUB_TOKEN not configured or placeholder. Using mock diff.")
        pr_diff = MOCK_DIFF

    # 2. Run LangGraph review workflow
    graph = create_review_graph()
    
    initial_state = {
        "repo": repo,
        "pr_number": pr_number,
        "pr_diff": pr_diff,
        "review_id": delivery_id,
        "context_chunks": [],
        "findings": [],
        "recommendation": "",
        "overall_confidence": 0.0,
        "summary": "",
        "has_critical": False,
        "hitl_action": "NONE",
        "reviewer_comments": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "latency_ms": 0,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        print(f"[Worker] Review workflow completed successfully. Recommendation: {final_state.get('recommendation')}")
        return {
            "status": "completed",
            "review_id": delivery_id,
            "recommendation": final_state.get("recommendation"),
            "findings_count": len(final_state.get("findings", [])),
        }
    except Exception as e:
        print(f"[Error] Review workflow failed: {e}")
        return {
            "status": "failed",
            "review_id": delivery_id,
            "error": str(e)
        }


class WorkerSettings:
    """ARQ reads this class to configure the worker process."""
    functions = [review_pr]
    redis_settings = None  # overridden at runtime
