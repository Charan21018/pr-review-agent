try:
    from github import Github
except Exception:  # pragma: no cover
    Github = None

import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_BASE_DELAY_SECONDS = 1.0
_FAILURE_THRESHOLD = 3
_CIRCUIT_TIMEOUT_SECONDS = 30.0

# Module-level circuit breaker state, shared across GitHubClient instances
# (mirrors the "github_api" breaker registered in backend/reliability/circuit_breaker.py,
# but kept synchronous here since post_review() is called from sync call sites).
_circuit_failure_count = 0
_circuit_opened_at: Optional[float] = None


def _circuit_is_open() -> bool:
    global _circuit_opened_at
    if _circuit_opened_at is None:
        return False
    if time.monotonic() - _circuit_opened_at >= _CIRCUIT_TIMEOUT_SECONDS:
        _circuit_opened_at = None  # cool-down elapsed; allow a probe through
        return False
    return True


def _record_success() -> None:
    global _circuit_failure_count, _circuit_opened_at
    _circuit_failure_count = 0
    _circuit_opened_at = None


def _record_failure() -> None:
    global _circuit_failure_count, _circuit_opened_at
    _circuit_failure_count += 1
    if _circuit_failure_count >= _FAILURE_THRESHOLD:
        _circuit_opened_at = time.monotonic()


class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if Github and self.token:
            self.client = Github(self.token)
        else:
            # No token, or PyGithub isn't installed: fall back to a stub so the
            # client can still be constructed. post_review() no-ops without a token.
            class _StubRepo:
                def get_pull(self, pull_number):
                    return self
                def create_review(self, event, body):
                    pass
                def create_issue_comment(self, body):
                    pass
            class _StubClient:
                def get_repo(self, repo_full_name):
                    return _StubRepo()
            self.client = _StubClient()

    def post_review(self, repo_full_name: str, pull_number: int, body: str, decision: str = "APPROVE"):
        """Post a review comment on a PR.

        Parameters:
            repo_full_name: e.g. "owner/repo"
            pull_number: PR number
            body: markdown text of the review
            decision: "APPROVE" or "REQUEST_CHANGES"

        Never raises: retries with exponential backoff, then trips a circuit
        breaker after repeated failures and routes to a dead-letter log line.
        """
        if not self.token:
            logger.warning("GITHUB_TOKEN not set; skipping review post for PR %s", pull_number)
            return

        if _circuit_is_open():
            logger.warning("GitHub API circuit breaker is open; skipping review post for PR %s", pull_number)
            print(f"[DLQ] Review posting failed for PR {pull_number}")
            return

        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                self._post_review_once(repo_full_name, pull_number, body, decision)
                _record_success()
                return
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "GitHub post_review attempt %d/%d failed for PR %s: %s",
                    attempt, _MAX_ATTEMPTS, pull_number, exc,
                )
                if attempt < _MAX_ATTEMPTS:
                    time.sleep(_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))

        _record_failure()
        logger.warning("Review posting failed for PR %s after %d attempts: %s", pull_number, _MAX_ATTEMPTS, last_exc)
        print(f"[DLQ] Review posting failed for PR {pull_number}")

    def _post_review_once(self, repo_full_name: str, pull_number: int, body: str, decision: str) -> None:
        repo = self.client.get_repo(repo_full_name)
        pr = repo.get_pull(pull_number)
        if decision.upper() == "APPROVE":
            pr.create_review(event="APPROVE", body=body)
        elif decision.upper() == "REQUEST_CHANGES":
            pr.create_review(event="REQUEST_CHANGES", body=body)
        else:
            pr.create_issue_comment(body)  # fallback as plain comment

    async def get_pull_request_diff(self, repo_full_name: str, pull_number: int) -> str:
        """Fetch the raw diff of a pull request using httpx."""
        import httpx
        url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pull_number}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3.diff",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(f"Failed to fetch PR diff: {response.status_code} - {response.text}")
            return response.text
