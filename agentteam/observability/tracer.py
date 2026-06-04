"""
AgentTeam OpenTelemetry Tracer Module

Provides tracing capabilities for AgentTeam operations with:
- Pre-configured span names
- Automatic attribute capture
- Context propagation
- Optional OpenTelemetry (graceful degradation if not available)
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Generator, Optional

# Try to import OpenTelemetry, but make it optional
try:
    from opentelemetry import trace
    from opentelemetry.trace import (
        Span,
        SpanKind,
        Status,
        StatusCode,
        Tracer,
        get_tracer,
    )
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.context import Context
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    Span = None
    SpanKind = None
    Status = None
    StatusCode = None
    Tracer = None
    get_tracer = None
    Context = None
    TraceContextTextMapPropagator = None

from agentteam.utils.logger import get_logger as get_basic_logger

logger = get_basic_logger(__name__)


class NoOpSpan:
    """No-operation span for when OpenTelemetry is not available."""

    def __init__(self, name: str):
        self.name = name
        self._attributes: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self._attributes[key] = value

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        self._attributes.update(attributes)

    def add_event(self, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class NoOpTracer:
    """No-operation tracer for when OpenTelemetry is not available."""

    def __init__(self, name: str):
        self.name = name

    def start_as_current_span(
        self,
        name: str,
        context: Optional[Any] = None,
        kind: Optional[Any] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> NoOpSpan:
        span = NoOpSpan(name)
        if attributes:
            span.set_attributes(attributes)
        return span

    def start_span(
        self,
        name: str,
        context: Optional[Any] = None,
        kind: Optional[Any] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> NoOpSpan:
        return self.start_as_current_span(name, context, kind, attributes)


class TracerWrapper:
    """
    Wrapper for OpenTelemetry tracer with graceful degradation.

    Provides:
    - Automatic fallback to NoOp when OTel unavailable
    - Common span attributes
    - Decorators and context managers
    """

    def __init__(
        self,
        name: str = "agentteam",
        version: Optional[str] = None,
    ):
        self.name = name
        self.version = version
        self._tracer: Optional[Any] = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Initialize the tracer if not already done."""
        if self._initialized:
            return

        if OTEL_AVAILABLE:
            try:
                self._tracer = get_tracer(self.name, self.version)
                self._initialized = True
                logger.debug(f"Initialized OpenTelemetry tracer: {self.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize OTel tracer: {e}")
                self._tracer = NoOpTracer(self.name)
                self._initialized = True
        else:
            self._tracer = NoOpTracer(self.name)
            self._initialized = True
            logger.debug("OpenTelemetry not available, using NoOp tracer")

    @property
    def tracer(self) -> Any:
        """Get the underlying tracer."""
        self._ensure_initialized()
        return self._tracer

    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        kind: Optional[Any] = None,
        attributes: Optional[dict[str, Any]] = None,
        context: Optional[Any] = None,
    ) -> Generator[Any, None, None]:
        """
        Start a new span as the current span.

        Args:
            name: Name of the span
            kind: Span kind (CLIENT, SERVER, PRODUCER, CONSUMER, INTERNAL)
            attributes: Initial attributes to set on the span
            context: Optional parent context

        Yields:
            The created span
        """
        self._ensure_initialized()

        # Add common attributes
        if attributes is None:
            attributes = {}
        attributes.setdefault("service.name", self.name)
        if self.version:
            attributes.setdefault("service.version", self.version)

        try:
            if OTEL_AVAILABLE and hasattr(self._tracer, "start_as_current_span"):
                with self._tracer.start_as_current_span(
                    name=name,
                    kind=kind,
                    context=context,
                ) as span:
                    if attributes:
                        span.set_attributes(attributes)
                    yield span
            else:
                span = self._tracer.start_as_current_span(name, attributes=attributes)
                try:
                    yield span
                finally:
                    span.end()
        except Exception as e:
            # Record exception on span
            if "span" in dir():
                try:
                    span.record_exception(e)
                except Exception:
                    pass
            raise

    def start_span(
        self,
        name: str,
        kind: Optional[Any] = None,
        attributes: Optional[dict[str, Any]] = None,
        context: Optional[Any] = None,
    ) -> Any:
        """
        Start a new span without making it current.

        Args:
            name: Name of the span
            kind: Span kind
            attributes: Initial attributes
            context: Optional parent context

        Returns:
            The created span
        """
        self._ensure_initialized()

        if attributes is None:
            attributes = {}
        attributes.setdefault("service.name", self.name)

        if OTEL_AVAILABLE and hasattr(self._tracer, "start_span"):
            return self._tracer.start_span(
                name=name,
                kind=kind,
                context=context,
            )
        return self._tracer.start_span(name, attributes=attributes)

    def create_span_decorator(
        self,
        name: Optional[str] = None,
        kind: Optional[Any] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> Callable:
        """
        Create a decorator that wraps a function in a span.

        Args:
            name: Span name (defaults to function name)
            kind: Span kind
            attributes: Additional attributes

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            span_name = name or f"{func.__module__}.{func.__qualname__}"

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.start_as_current_span(span_name, kind=kind, attributes=attributes) as span:
                    try:
                        result = func(*args, **kwargs)
                        if OTEL_AVAILABLE:
                            span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        if OTEL_AVAILABLE:
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                            span.record_exception(e)
                        raise

            return wrapper
        return decorator


# Global tracer instance
tracer = TracerWrapper(name="agentteam", version="0.5.1")


def trace_async(
    name: Optional[str] = None,
    kind: Optional[Any] = None,
    attributes: Optional[dict[str, Any]] = None,
) -> Callable:
    """
    Decorator for tracing async functions.

    Args:
        name: Optional span name
        kind: Optional span kind
        attributes: Optional initial attributes

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name, kind=kind, attributes=attributes) as span:
                try:
                    result = await func(*args, **kwargs)
                    if OTEL_AVAILABLE:
                        span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    if OTEL_AVAILABLE:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                    raise

        return wrapper
    return decorator


def trace_sync(
    name: Optional[str] = None,
    kind: Optional[Any] = None,
    attributes: Optional[dict[str, Any]] = None,
) -> Callable:
    """
    Decorator for tracing sync functions.

    Args:
        name: Optional span name
        kind: Optional span kind
        attributes: Optional initial attributes

    Returns:
        Decorated function
    """
    return tracer.create_span_decorator(name, kind, attributes)
