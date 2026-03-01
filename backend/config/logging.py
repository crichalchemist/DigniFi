"""
Structured logging utilities for DigniFi.

Provides JSON formatting and request-ID correlation for audit compliance.
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from django.http import HttpRequest, HttpResponse


# Thread-local storage for request context (request ID, user, IP).
_request_context = threading.local()


def get_request_id() -> str:
    """Retrieve the current request's correlation ID, or 'no-request' outside HTTP."""
    return getattr(_request_context, "request_id", "no-request")


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "request_id": getattr(record, "request_id", get_request_id()),
        }

        # Include extra fields from record if present
        for key in ("user_id", "ip_address", "path", "method", "status_code", "upl_sensitive"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class RequestIDFilter(logging.Filter):
    """Injects the current request ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class RequestIDMiddleware:
    """
    Middleware that assigns a unique request ID to each HTTP request.

    Reads X-Request-ID header if present (from reverse proxy),
    otherwise generates a new UUID. Stores it in thread-local
    storage and includes it in the response headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get(
            "HTTP_X_REQUEST_ID", str(uuid.uuid4())
        )

        _request_context.request_id = request_id
        _request_context.user_id = None

        response = self.get_response(request)

        # Attach request ID to response for tracing
        response["X-Request-ID"] = request_id

        # Clean up thread-local storage
        _request_context.request_id = "no-request"
        _request_context.user_id = None

        return response
