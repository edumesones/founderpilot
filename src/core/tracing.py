"""Langfuse tracing integration for InboxPilot."""

import os
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Generator, TypeVar
from uuid import uuid4

from langfuse import Langfuse
from langfuse.decorators import observe


# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


# Global Langfuse client (lazy-initialized)
_langfuse: Langfuse | None = None


def get_langfuse() -> Langfuse | None:
    """Get or create Langfuse client.

    Returns:
        Langfuse client if configured, None otherwise
    """
    global _langfuse

    if _langfuse is not None:
        return _langfuse

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        return None

    _langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )

    return _langfuse


def shutdown_tracing() -> None:
    """Shutdown Langfuse client and flush pending traces."""
    global _langfuse
    if _langfuse:
        _langfuse.flush()
        _langfuse.shutdown()
        _langfuse = None


class TraceContext:
    """Context manager for Langfuse traces."""

    def __init__(
        self,
        name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ):
        """Initialize trace context.

        Args:
            name: Trace name (e.g., "inbox_pilot.process_email")
            user_id: User ID for the trace
            session_id: Session ID for grouping related traces
            metadata: Additional metadata to attach
            tags: Tags for filtering traces
        """
        self.name = name
        self.user_id = user_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.tags = tags or []
        self.trace = None
        self.trace_id = str(uuid4())

    def __enter__(self) -> "TraceContext":
        """Start the trace."""
        langfuse = get_langfuse()
        if langfuse:
            self.trace = langfuse.trace(
                name=self.name,
                user_id=self.user_id,
                session_id=self.session_id,
                metadata=self.metadata,
                tags=self.tags,
                id=self.trace_id,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End the trace."""
        if self.trace and exc_type:
            # Mark trace as failed if exception occurred
            self.trace.update(
                level="ERROR",
                status_message=str(exc_val),
            )

    def span(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> "SpanContext":
        """Create a child span.

        Args:
            name: Span name
            metadata: Additional metadata

        Returns:
            SpanContext manager
        """
        return SpanContext(
            parent=self,
            name=name,
            metadata=metadata,
        )

    def log_generation(
        self,
        name: str,
        model: str,
        input_text: str,
        output_text: str,
        usage: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an LLM generation.

        Args:
            name: Generation name (e.g., "classify", "draft")
            model: Model name
            input_text: Input prompt
            output_text: Model output
            usage: Token usage dict with keys: prompt_tokens, completion_tokens
            metadata: Additional metadata
        """
        if not self.trace:
            return

        self.trace.generation(
            name=name,
            model=model,
            input=input_text,
            output=output_text,
            usage=usage,
            metadata=metadata or {},
        )

    def log_event(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        level: str = "DEFAULT",
    ) -> None:
        """Log an event within the trace.

        Args:
            name: Event name
            metadata: Event metadata
            level: Log level (DEFAULT, DEBUG, WARNING, ERROR)
        """
        if not self.trace:
            return

        self.trace.event(
            name=name,
            metadata=metadata or {},
            level=level,
        )

    def update(
        self,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update trace with final output.

        Args:
            output: Final output to record
            metadata: Additional metadata to merge
        """
        if not self.trace:
            return

        update_data = {}
        if output is not None:
            update_data["output"] = output
        if metadata:
            update_data["metadata"] = {**self.metadata, **metadata}

        if update_data:
            self.trace.update(**update_data)


class SpanContext:
    """Context manager for Langfuse spans within a trace."""

    def __init__(
        self,
        parent: TraceContext,
        name: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize span context.

        Args:
            parent: Parent trace context
            name: Span name
            metadata: Additional metadata
        """
        self.parent = parent
        self.name = name
        self.metadata = metadata or {}
        self.span = None
        self.start_time = None

    def __enter__(self) -> "SpanContext":
        """Start the span."""
        self.start_time = datetime.utcnow()
        if self.parent.trace:
            self.span = self.parent.trace.span(
                name=self.name,
                metadata=self.metadata,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End the span."""
        if self.span:
            update_data = {}
            if exc_type:
                update_data["level"] = "ERROR"
                update_data["status_message"] = str(exc_val)
            if self.start_time:
                duration = (datetime.utcnow() - self.start_time).total_seconds()
                update_data["metadata"] = {
                    **self.metadata,
                    "duration_seconds": duration,
                }
            if update_data:
                self.span.update(**update_data)

    def update(
        self,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update span with output.

        Args:
            output: Span output
            metadata: Additional metadata
        """
        if not self.span:
            return

        update_data = {}
        if output is not None:
            update_data["output"] = output
        if metadata:
            update_data["metadata"] = {**self.metadata, **metadata}

        if update_data:
            self.span.update(**update_data)


@contextmanager
def trace_agent_run(
    message_id: str,
    user_id: str,
) -> Generator[TraceContext, None, None]:
    """Create a trace for an agent run.

    Args:
        message_id: Gmail message ID
        user_id: User ID

    Yields:
        TraceContext for the agent run
    """
    ctx = TraceContext(
        name="inbox_pilot.process_email",
        user_id=user_id,
        session_id=f"user_{user_id}",
        metadata={"message_id": message_id},
        tags=["inbox_pilot", "agent"],
    )
    with ctx:
        yield ctx


def traced(name: str | None = None) -> Callable[[F], F]:
    """Decorator to trace a function with Langfuse.

    Args:
        name: Optional name override for the trace

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        trace_name = name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            langfuse = get_langfuse()
            if not langfuse:
                return await func(*args, **kwargs)

            trace = langfuse.trace(name=trace_name)
            try:
                result = await func(*args, **kwargs)
                trace.update(output=str(result)[:500])  # Truncate output
                return result
            except Exception as e:
                trace.update(level="ERROR", status_message=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            langfuse = get_langfuse()
            if not langfuse:
                return func(*args, **kwargs)

            trace = langfuse.trace(name=trace_name)
            try:
                result = func(*args, **kwargs)
                trace.update(output=str(result)[:500])
                return result
            except Exception as e:
                trace.update(level="ERROR", status_message=str(e))
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
