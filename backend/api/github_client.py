try:
    from github import Github, GithubException
except Exception:  # pragma: no cover
    Github = None
    GithubException = Exception

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

    def post_review(self, repo_full_name: str, pull_number: int, body: str, decision: str = "APPROVE") -> bool:
        """Post a review comment on a PR.

        Parameters:
            repo_full_name: e.g. "owner/repo"
            pull_number: PR number
            body: markdown text of the review
            decision: "APPROVE" or "REQUEST_CHANGES"

        Returns True if the review was actually posted, False otherwise. Never
        raises: retries with exponential backoff, then trips a circuit breaker
        after repeated failures and routes to a dead-letter log line.
        """
        if not self.token:
            logger.warning("GITHUB_TOKEN not set; skipping review post for PR %s", pull_number)
            return False

        if _circuit_is_open():
            logger.warning("GitHub API circuit breaker is open; skipping review post for PR %s", pull_number)
            print(f"[DLQ] Review posting failed for PR {pull_number}")
            return False

        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                self._post_review_once(repo_full_name, pull_number, body, decision)
                _record_success()
                return True
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
        return False

    def _post_review_once(self, repo_full_name: str, pull_number: int, body: str, decision: str) -> None:
        repo = self.client.get_repo(repo_full_name)
        pr = repo.get_pull(pull_number)
        event = decision.upper() if decision.upper() in ("APPROVE", "REQUEST_CHANGES") else None
        if event is None:
            pr.create_issue_comment(body)  # fallback as plain comment
            return

        try:
            pr.create_review(event=event, body=body)
        except GithubException as exc:
            # GitHub rejects APPROVE/REQUEST_CHANGES from the same account that
            # opened the PR (common in local/solo testing where GITHUB_TOKEN
            # belongs to the PR author). A plain COMMENT review has no such
            # restriction, so fall back to that rather than burning the retry
            # budget on a call that will never succeed.
            if self._is_self_review_rejection(exc):
                logger.info(
                    "GitHub rejected %s on PR %s as a self-review; falling back to a COMMENT review.",
                    event, pull_number,
                )
                pr.create_review(event="COMMENT", body=body)
            else:
                raise

    @staticmethod
    def _is_self_review_rejection(exc: "GithubException") -> bool:
        if getattr(exc, "status", None) != 422:
            return False
        data = getattr(exc, "data", None)
        errors = data.get("errors", []) if isinstance(data, dict) else []
        return any("own pull request" in str(e).lower() for e in errors)

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
