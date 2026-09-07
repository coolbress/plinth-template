"""The container's entry point: `python -m <package>`, what the Dockerfile's CMD runs.

No framework is chosen here; what serves the application is this project's
decision, and a `uvicorn` or `flask` planted here would be a stub in every
project that does not use it. Replace the body of `main()` when a server
arrives; the logging setup can stay.

Logs are one JSON object per line on stdout, so a container's output is
collected as is. Standard library only. Metrics, traces and SLOs live outside
the repository, in whatever the deployment uses.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from . import greet

# The fields every LogRecord carries. Anything else came in through
# `logger.info("...", extra={...})` and is kept: context in fields is the
# point of structured logs.
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure(level: int = logging.INFO) -> None:
    """Point the root logger at stdout in JSON. Safe to call more than once."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def main() -> None:
    configure()
    logging.getLogger(__package__).info("started", extra={"greeting": greet("world")})


if __name__ == "__main__":
    main()
