"""Centralized logging setup for ByteBabel."""

from __future__ import annotations

import logging
import logging.handlers
import queue
from pathlib import Path

LOG_DIR  = Path.home() / ".bytebabel" / "logs"
LOG_FILE = LOG_DIR / "app.log"

# Global queue drained by LogPanel in the UI thread
ui_log_queue: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=2000)


def setup_logging(level: int = logging.DEBUG) -> None:
    """Configure the root 'bytebabel' logger. Safe to call multiple times."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("bytebabel")
    if root.handlers:
        return  # already initialised
    root.setLevel(level)
    root.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    short_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Rotating file — 5 MB × 3 backups
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console (stderr)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(short_fmt)

    # UI queue handler
    uh = _UIQueueHandler(ui_log_queue)
    uh.setLevel(logging.DEBUG)

    root.addHandler(fh)
    root.addHandler(ch)
    root.addHandler(uh)


class _UIQueueHandler(logging.Handler):
    def __init__(self, log_queue: "queue.Queue[logging.LogRecord]") -> None:
        super().__init__()
        self._queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait(record)
        except Exception:
            pass


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under 'bytebabel.*'."""
    return logging.getLogger(f"bytebabel.{name}")
