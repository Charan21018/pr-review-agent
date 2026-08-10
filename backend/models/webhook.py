"""backend/models/webhook.py — GitHub webhook payload models."""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class PullRequestInfo(BaseModel):
    number: int
    title: str
    state: str
    diff_url: Optional[str] = None
    head: Optional[Dict[str, Any]] = None
    base: Optional[Dict[str, Any]] = None


class RepositoryInfo(BaseModel):
    full_name: str
    name: str
    default_branch: Optional[str] = "main"


class SenderInfo(BaseModel):
    login: str
    id: Optional[int] = None


class WebhookEvent(BaseModel):
    """Parsed GitHub pull_request webhook payload."""
    action: str
    pull_request: Optional[PullRequestInfo] = None
    repository: Optional[RepositoryInfo] = None
    sender: Optional[SenderInfo] = None
    installation: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookEvent":
        """Parse raw webhook payload dict into typed model."""
        pr_data = data.get("pull_request", {})
        repo_data = data.get("repository", {})
        sender_data = data.get("sender", {})
        return cls(
            action=data.get("action", ""),
            pull_request=PullRequestInfo(**pr_data) if pr_data else None,
            repository=RepositoryInfo(**repo_data) if repo_data else None,
            sender=SenderInfo(**sender_data) if sender_data else None,
        )
