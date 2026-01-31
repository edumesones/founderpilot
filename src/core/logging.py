"""Structured logging configuration for InboxPilot."""

import json
import logging
import sys
from datetime import datetime
from typing import Any

import structlog
from structlog.types import Processor


class JSONFormatter(logging.Formatter):
    """JSON formatter for standard logging handlers."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = str(record.user_id)
        if hasattr(record, "message_id"):
            log_data["message_id"] = record.message_id
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "node"):
            log_data["node"] = record.node
        if hasattr(record, "category"):
            log_data["category"] = record.category
        if hasattr(record, "confidence"):
            log_data["confidence"] = record.confidence
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def add_app_context(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add application context to log entries."""
    event_dict["app"] = "inbox_pilot"
    event_dict["version"] = "1.0.0"
    return event_dict


def add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO timestamp to log entries."""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    json_output: bool = True,
    development: bool = False,
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        json_output: Whether to output JSON format
        development: Whether to use development-friendly formatting
    """
    # Shared processors for structlog
    shared_processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_timestamp,
        add_app_context,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if development:
        # Development: colorful console output
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure standard logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper()),
        )
    else:
        # Production: JSON output
        structlog.configure(
            processors=shared_processors + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure standard logging with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=shared_processors,
            )
        )

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(getattr(logging, log_level.upper()))

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Bound structlog logger
    """
    return structlog.get_logger(name)


class AgentLogger:
    """Specialized logger for InboxPilot agent operations."""

    def __init__(self, user_id: str | None = None, trace_id: str | None = None):
        """Initialize agent logger.

        Args:
            user_id: User ID for context
            trace_id: Trace ID for request correlation
        """
        self._logger = get_logger("inbox_pilot.agent")
        self._context = {}
        if user_id:
            self._context["user_id"] = user_id
        if trace_id:
            self._context["trace_id"] = trace_id

    def bind(self, **kwargs: Any) -> "AgentLogger":
        """Bind additional context to logger.

        Returns:
            New logger with bound context
        """
        new_logger = AgentLogger()
        new_logger._logger = self._logger.bind(**self._context, **kwargs)
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def node_start(self, node_name: str, message_id: str) -> None:
        """Log start of agent node execution."""
        self._logger.info(
            "node_started",
            node=node_name,
            message_id=message_id,
            **self._context,
        )

    def node_complete(
        self,
        node_name: str,
        message_id: str,
        duration_ms: float,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Log completion of agent node execution."""
        log_data = {
            "node": node_name,
            "message_id": message_id,
            "duration_ms": round(duration_ms, 2),
            **self._context,
        }
        if result:
            # Add key metrics from result
            if "category" in result:
                log_data["category"] = result["category"]
            if "confidence" in result:
                log_data["confidence"] = result["confidence"]
            if "action" in result:
                log_data["action"] = result["action"]

        self._logger.info("node_completed", **log_data)

    def node_error(
        self,
        node_name: str,
        message_id: str,
        error: Exception,
    ) -> None:
        """Log error in agent node."""
        self._logger.error(
            "node_error",
            node=node_name,
            message_id=message_id,
            error_type=type(error).__name__,
            error_message=str(error),
            **self._context,
        )

    def classification(
        self,
        message_id: str,
        category: str,
        confidence: float,
        reasoning: str,
    ) -> None:
        """Log email classification result."""
        self._logger.info(
            "email_classified",
            message_id=message_id,
            category=category,
            confidence=round(confidence, 3),
            reasoning=reasoning[:100],  # Truncate for logs
            **self._context,
        )

    def escalation(
        self,
        message_id: str,
        reason: str,
        slack_channel: str | None = None,
    ) -> None:
        """Log escalation to human."""
        self._logger.info(
            "email_escalated",
            message_id=message_id,
            reason=reason,
            slack_channel=slack_channel,
            **self._context,
        )

    def action_taken(
        self,
        message_id: str,
        action: str,
        human_initiated: bool = False,
    ) -> None:
        """Log action taken on email."""
        self._logger.info(
            "action_taken",
            message_id=message_id,
            action=action,
            human_initiated=human_initiated,
            **self._context,
        )

    def llm_call(
        self,
        provider: str,
        model: str,
        operation: str,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Log LLM API call."""
        self._logger.info(
            "llm_call",
            provider=provider,
            model=model,
            operation=operation,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=round(duration_ms, 2) if duration_ms else None,
            **self._context,
        )

    def gmail_api_call(
        self,
        operation: str,
        message_id: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Log Gmail API call."""
        log_level = "info" if success else "error"
        getattr(self._logger, log_level)(
            "gmail_api_call",
            operation=operation,
            message_id=message_id,
            success=success,
            error=error,
            **self._context,
        )

    def slack_api_call(
        self,
        operation: str,
        channel: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Log Slack API call."""
        log_level = "info" if success else "error"
        getattr(self._logger, log_level)(
            "slack_api_call",
            operation=operation,
            channel=channel,
            success=success,
            error=error,
            **self._context,
        )
