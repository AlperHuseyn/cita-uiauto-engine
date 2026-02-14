"""
@file actionlogger.py
@brief Central action logging facility for UI automation actions.
"""

from __future__ import annotations

import json
import os
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class ActionLogger:
    """Thread-safe action logger with line/jsonl output."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled = False
        self._console = True
        self._file_path: Optional[str] = None
        self._level = "INFO"
        self._run_id = "default"
        self._format = "line"
        self._max_traceback_chars = 4000
        self._sample_retry_events = 1

    def configure(
        self,
        *,
        console: bool = True,
        file_path: Optional[str] = None,
        level: str = "INFO",
        run_id: Optional[str] = None,
        format: str = "line",
        max_traceback_chars: int = 4000,
        sample_retry_events: int = 1,
    ) -> None:
        """Configure logger settings."""
        fmt = (format or "line").lower()
        if fmt not in {"line", "jsonl"}:
            raise ValueError("ActionLogger format must be 'line' or 'jsonl'")

        with self._lock:
            self._console = bool(console)
            self._file_path = file_path
            self._level = level.upper()
            self._format = fmt
            self._max_traceback_chars = max(256, int(max_traceback_chars))
            self._sample_retry_events = max(1, int(sample_retry_events))
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

    def should_log_retry_attempt(self, attempt: int) -> bool:
        """Sampling strategy for retry attempt logs to avoid log spam."""
        if attempt <= 1:
            return True
        return attempt % self._sample_retry_events == 0

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
        action_id: Optional[str] = None,
        phase: Optional[str] = None,
        attempt: Optional[int] = None,
        event: Optional[str] = None,
    ) -> None:
        """Emit a log event."""
        if not self._enabled:
            return

        timestamp = time.strftime("%H:%M:%S")
        meta = dict(metadata or {})
        meta = self._redact_metadata(action, meta)

        event_obj: Dict[str, Any] = {
            "timestamp": timestamp,
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": self._level,
            "event": event or "action",
            "action": action,
            "action_id": action_id,
            "element": element,
            "window": window,
            "phase": phase,
            "status": status,
            "attempt": attempt,
            "duration_ms": duration_ms,
            "metadata": meta,
            "run_id": self._run_id,
        }

        if exception is not None:
            event_obj["exception"] = self._format_exception(exception)

        line = self._format_output(event_obj)

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

    def _format_output(self, event: Dict[str, Any]) -> str:
        if self._format == "jsonl":
            return json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        return self._format_line(event)

    def _format_line(self, event: Dict[str, Any]) -> str:
        parts = [
            event.get("timestamp", ""),
            event.get("level", "INFO"),
            event.get("action", ""),
        ]

        event_name = event.get("event")
        if event_name:
            parts.append(f"event={event_name}")

        action_id = event.get("action_id")
        if action_id:
            parts.append(f"action_id={action_id}")

        element = event.get("element")
        if element:
            parts.append(f"element='{element}'")

        window = event.get("window")
        if window:
            parts.append(f"window='{window}'")

        phase = event.get("phase")
        if phase:
            parts.append(f"phase={phase}")

        attempt = event.get("attempt")
        if attempt is not None:
            parts.append(f"attempt={attempt}")

        status = event.get("status")
        if status:
            parts.append(f"status={status}")

        duration = event.get("duration_ms")
        if duration is not None:
            parts.append(f"duration_ms={duration}")

        run_id = event.get("run_id")
        if run_id:
            parts.append(f"run_id={run_id}")

        meta = event.get("metadata") or {}
        for key, value in meta.items():
            parts.append(f"{key}={value}")

        exc = event.get("exception")
        if exc:
            parts.append(f"exc_type={exc.get('type')}")
            parts.append(f"exc_message={exc.get('message')}")
            if exc.get("cause_type"):
                parts.append(f"cause_type={exc.get('cause_type')}")

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

    def _format_exception(self, exception: BaseException) -> Dict[str, Any]:
        tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        if len(tb) > self._max_traceback_chars:
            tb = tb[: self._max_traceback_chars] + "...<truncated>"

        cause = getattr(exception, "__cause__", None)
        context = getattr(exception, "__context__", None)

        return {
            "type": type(exception).__name__,
            "message": str(exception),
            "traceback": tb.strip(),
            "cause_type": type(cause).__name__ if cause is not None else None,
            "cause_message": str(cause) if cause is not None else None,
            "context_type": type(context).__name__ if context is not None else None,
            "context_message": str(context) if context is not None else None,
        }


ACTION_LOGGER = ActionLogger()