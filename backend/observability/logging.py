"""backend/observability/logging.py — Structured JSON logging setup.

Call ``configure_logging()`` once at startup (in run.py / run_worker.py).
After that, all ``logging.getLogger(name)`` calls produce JSON-structured
output that is compatible with Cloud Logging, Datadog, and Loki.

JSON fields per log line:
  - timestamp   (ISO-8601)
  - level       (DEBUG / INFO / WARNING / ERROR / CRITICAL)
  - logger      (dotted module name)
  - message
  - review_id   (injected from ContextVar when present)
  - **extra     (any kwargs passed to the logger call)
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.observability.workflow_context import get_review_id


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject review_id from ContextVar if set
        review_id = get_review_id()
        if review_id:
            log_entry["review_id"] = str(review_id)

        # Attach any extra fields the caller provided
        skip_fields = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in skip_fields and not key.startswith("_"):
                log_entry[key] = value

        # Attach exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    stream=None,
) -> None:
    """Configure the root logger.

    Args:
        level: Log level name (e.g. "DEBUG", "INFO").
        json_output: If True (default for production), emit JSON lines.
                     If False, emit human-readable text (useful for local dev).
        stream: Output stream. Defaults to sys.stdout.
    """
    stream = stream or sys.stdout

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any existing handlers to avoid duplicate output
    root.handlers.clear()

    handler = logging.StreamHandler(stream)
    if json_output:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # Silence overly noisy third-party loggers
    for noisy in ("httpx", "httpcore", "asyncpg", "urllib3", "opentelemetry"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configured",
        extra={"log_level": level, "json_output": json_output},
    )
