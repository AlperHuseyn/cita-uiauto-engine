# uiauto/timinglogger.py
"""
@file timinglogger.py
@brief Timing-specific logger for wait/retry observability.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional


class TimingLogger:
    """Thread-safe timing logger with console/file output."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled = False
        self._console = True
        self._file_path: Optional[str] = None
        self._level = "INFO"

    def configure(
        self,
        *,
        console: bool = True,
        file_path: Optional[str] = None,
        level: str = "INFO",
    ) -> None:
        """Configure logger settings."""
        with self._lock:
            self._console = bool(console)
            self._file_path = file_path
            self._level = level.upper()

    def enable(self) -> None:
        """Enable logging."""
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        """Disable logging."""
        with self._lock:
            self._enabled = False

    def is_enabled(self) -> bool:
        """Return True if logging is enabled."""
        return self._enabled

    def log(
        self,
        *,
        event: str,
        description: Optional[str] = None,
        status: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a timing log event."""
        if not self._enabled:
            return

        timestamp = time.strftime("%H:%M:%S")
        meta = metadata or {}
        level_tag = f"[{status.lower()}]"
        parts = [
            level_tag,
            "[timing]",
            f"time={timestamp}",
            f"event={event}",
        ]
        if description:
            parts.append(f"description={description}")
        for key, value in meta.items():
            parts.append(f"{key}={value}")

        line = " ".join(parts)

        if self._console:
            print(line, flush=True)

        if self._file_path:
            self._write_file(line)

    def _write_file(self, line: str) -> None:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self._file_path)) or ".", exist_ok=True)
            with open(self._file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


TIMING_LOGGER = TimingLogger()