"""backend/observability/tracing.py — OpenTelemetry span helpers.

Wraps the OTel SDK so the rest of the codebase never imports opentelemetry directly.
If the OTel SDK is not installed or the OTEL_EXPORTER_OTLP_ENDPOINT env var is
not set the module degrades gracefully to no-op stubs — the service still runs.
"""
import os
import functools
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional

# ---------------------------------------------------------------------------
# Graceful import — OTel is optional at runtime
# ---------------------------------------------------------------------------
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OTEL_AVAILABLE = False


class _NoOpSpan:
    """Returned when OTel is unavailable — all attribute/event calls are silent."""

    def set_attribute(self, key: str, value: Any) -> None:  # noqa: D401
        pass

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        pass

    def record_exception(self, exc: Exception) -> None:
        pass

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TracingManager:
    """Singleton wrapper around the OTel TracerProvider.

    Initialise once at startup via ``TracingManager.setup()``.  All agents
    obtain spans via ``TracingManager.get_tracer(name).start_as_current_span()``.
    """

    _tracer_provider: Optional[Any] = None

    @classmethod
    def setup(
        cls,
        service_name: str = "ai-pr-review-agent",
        otlp_endpoint: Optional[str] = None,
    ) -> None:
        """Configure and register the global OTel TracerProvider.

        No-ops if OTel SDK is not installed or endpoint is absent.
        """
        if not _OTEL_AVAILABLE:
            return

        endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not endpoint:
            return

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        cls._tracer_provider = provider

    @classmethod
    def get_tracer(cls, name: str = "pr-review") -> Any:
        """Return an OTel Tracer, or a no-op object if OTel is unavailable."""
        if _OTEL_AVAILABLE and cls._tracer_provider is not None:
            return trace.get_tracer(name)
        return _NoOpTracer()

    @classmethod
    def shutdown(cls) -> None:
        if cls._tracer_provider is not None and _OTEL_AVAILABLE:
            cls._tracer_provider.shutdown()


class _NoOpTracer:
    """No-op tracer returned when OTel SDK is absent or unconfigured."""

    def start_as_current_span(self, name: str, **kwargs):
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            yield _NoOpSpan()

        return _ctx()

    def start_span(self, name: str, **kwargs) -> _NoOpSpan:
        return _NoOpSpan()


# ---------------------------------------------------------------------------
# Convenience decorator
# ---------------------------------------------------------------------------

def traced(span_name: Optional[str] = None, tracer_name: str = "pr-review"):
    """Decorator that wraps an async function in an OTel span.

    Usage::

        @traced("security_agent.run")
        async def run(self, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        name = span_name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = TracingManager.get_tracer(tracer_name)
            with tracer.start_as_current_span(name) as span:
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    raise

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Module-level singleton tracer for quick use
# ---------------------------------------------------------------------------
tracer = TracingManager.get_tracer()
