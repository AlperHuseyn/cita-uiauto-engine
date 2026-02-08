"""
@file actionlogger.py
@brief Central action logging facility for UI automation actions.
"""

from __future__ import annotations

import os
import threading
import time
import traceback
from typing import Any, Dict, Optional


class ActionLogger:
    """Thread-safe action logger with console/file output."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled = False
        self._console = True
        self._file_path: Optional[str] = None
        self._level = "INFO"
        self._run_id = "default"

    def configure(
        self,
        *,
        console: bool = True,
        file_path: Optional[str] = None,
        level: str = "INFO",
        run_id: Optional[str] = None,
    ) -> None:
        """Configure logger settings."""
        with self._lock:
            self._console = bool(console)
            self._file_path = file_path
            self._level = level.upper()
            if run_id:
                self._run_id = run_id

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

    def set_run_id(self, run_id: str) -> None:
        """Set current run_id."""
        if run_id:
            with self._lock:
                self._run_id = run_id

    def log(
        self,
        *,
        action: str,
        element: Optional[str] = None,
        window: Optional[str] = None,
        status: str = "ok",
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        exception: Optional[BaseException] = None,
    ) -> None:
        """Emit a log event."""
        if not self._enabled:
            return

        timestamp = time.strftime("%H:%M:%S")
        meta = dict(metadata or {})
        meta = self._redact_metadata(action, meta)

        event: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": self._level,
            "action": action,
            "element": element,
            "window": window,
            "status": status,
            "duration_ms": duration_ms,
            "metadata": meta,
            "run_id": self._run_id,
        }

        if exception is not None:
            event["exception"] = self._format_exception(exception)

        line = self._format_line(event)

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

    def _format_line(self, event: Dict[str, Any]) -> str:
        parts = [
            event.get("timestamp", ""),
            event.get("level", "INFO"),
            event.get("action", ""),
        ]
        element = event.get("element")
        if element:
            parts.append(f"element='{element}'")
        window = event.get("window")
        if window:
            parts.append(f"window='{window}'")
        status = event.get("status")
        if status:
            parts.append(f"status={status}")
        duration = event.get("duration_ms")
        if duration is not None:
            parts.append(f"duration_ms={duration}")

        meta = event.get("metadata") or {}
        for key, value in meta.items():
            parts.append(f"{key}={value}")

        exc = event.get("exception")
        if exc:
            parts.append(f"exc_type={exc.get('type')}")
            parts.append(f"exc_message={exc.get('message')}")

        return " | ".join(parts)

    def _redact_metadata(self, action: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        sensitive_keys = {"password", "passwd", "secret", "token"}
        redacted = {}
        for key, value in metadata.items():
            if key.lower() in sensitive_keys:
                redacted[key] = "***"
                continue
            if action in {"type", "set_text", "click_and_type"} and key == "text":
                redacted[key] = self._mask_text(str(value))
                continue
            redacted[key] = value
        return redacted

    @staticmethod
    def _mask_text(text: str, max_visible: int = 10) -> str:
        if len(text) <= max_visible:
            return text
        return f"{text[:max_visible]}..."

    @staticmethod
    def _format_exception(exception: BaseException) -> Dict[str, Any]:
        tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        return {
            "type": type(exception).__name__,
            "message": str(exception),
            "traceback": tb.strip(),
        }


ACTION_LOGGER = ActionLogger()