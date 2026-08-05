import os


class Settings:
    """Reads configuration from environment variables at access time.

    Reading lazily (via @property) means monkeypatch.setenv() in tests
    takes effect without needing importlib.reload().
    """

    @property
    def github_webhook_secret(self) -> str:
        return os.getenv("GITHUB_WEBHOOK_SECRET", "test-secret-for-ci")

    @property
    def redis_url(self) -> str:
        return os.getenv("REDIS_URL", "redis://localhost:6379")

    @property
    def tiger_database_url(self) -> str:
        return os.getenv("TIGER_DATABASE_URL", "postgresql://localhost/pr_review")


settings = Settings()
