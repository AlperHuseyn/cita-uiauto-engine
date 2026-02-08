"""
@file loghub.py
@brief In-memory log hub for streaming action logs by run_id.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple


class LogHub:
    """Run-based log hub with ring buffers and subscriber callbacks."""

    def __init__(self, maxlen: int = 2000):
        self._maxlen = maxlen
        self._lock = threading.Lock()
        self._buffers: Dict[str, Deque[Dict[str, Any]]] = {}
        self._counters: Dict[str, int] = {}
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def publish(self, run_id: str, event: Dict[str, Any]) -> None:
        """Publish a log event for a run_id."""
        with self._lock:
            buffer = self._buffers.setdefault(run_id, deque(maxlen=self._maxlen))
            counter = self._counters.get(run_id, 0) + 1
            self._counters[run_id] = counter
            event = dict(event)
            event["id"] = counter
            buffer.append(event)
            subscribers = list(self._subscribers.get(run_id, []))
        for callback in subscribers:
            callback(event)

    def subscribe(self, run_id: str, callback: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        """Subscribe to run_id events. Returns an unsubscribe function."""
        with self._lock:
            self._subscribers.setdefault(run_id, []).append(callback)

        def _unsubscribe() -> None:
            with self._lock:
                subs = self._subscribers.get(run_id, [])
                if callback in subs:
                    subs.remove(callback)

        return _unsubscribe

    def get_since(self, run_id: str, cursor: int) -> Tuple[List[Dict[str, Any]], int]:
        """Get events since cursor (exclusive)."""
        with self._lock:
            buffer = list(self._buffers.get(run_id, []))
            items = [item for item in buffer if item.get("id", 0) > cursor]
            next_cursor = items[-1]["id"] if items else cursor
        return items, next_cursor

    def clear(self, run_id: Optional[str] = None) -> None:
        """Clear buffers (for one run_id or all)."""
        with self._lock:
            if run_id is None:
                self._buffers.clear()
                self._counters.clear()
                self._subscribers.clear()
            else:
                self._buffers.pop(run_id, None)
                self._counters.pop(run_id, None)
                self._subscribers.pop(run_id, None)


LOG_HUB = LogHub()