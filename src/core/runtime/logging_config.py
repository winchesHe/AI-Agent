"""Logging configuration driven by the runtime profile."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(
    level: str = "INFO",
    log_path: str | None = None,
    max_bytes: int = 10_485_760,
    backup_count: int = 5,
) -> None:
    """Configure the root logger with a stream handler and optional file handler."""
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    if log_path is not None:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
