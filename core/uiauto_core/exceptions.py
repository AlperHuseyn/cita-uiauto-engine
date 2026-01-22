# uiauto/exceptions.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class UIAutoError(Exception):
    """Base exception for the framework."""


class ConfigError(UIAutoError):
    """Raised when YAML/JSON configuration is invalid."""


class TimeoutError(UIAutoError):
    """Raised when a wait/retry times out."""


@dataclass
class LocatorAttempt:
    kind: str
    locator: Dict[str, Any]
    error: Optional[str] = None


class WindowNotFoundError(UIAutoError):
    def __init__(
        self,
        window_name: str,
        attempts: List[LocatorAttempt],
        timeout: float,
        last_error: Optional[str] = None,
        artifacts: Optional[Dict[str, str]] = None,
    ):
        self.window_name = window_name
        self.attempts = attempts
        self.timeout = timeout
        self.last_error = last_error
        self.artifacts = artifacts or {}
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = [
            f"WindowNotFoundError: window='{self.window_name}' timeout={self.timeout}s",
        ]
        if self.last_error:
            lines.append(f"Last error: {self.last_error}")
        lines.append("Attempts:")
        for i, a in enumerate(self.attempts, start=1):
            lines.append(f"  {i}. {a.kind}: {a.locator} err={a.error}")
        if self.artifacts:
            lines.append(f"Artifacts: {self.artifacts}")
        return "\n".join(lines)


class ElementNotFoundError(UIAutoError):
    def __init__(
        self,
        element_name: str,
        window_name: str,
        attempts: List[LocatorAttempt],
        timeout: float,
        last_error: Optional[str] = None,
        artifacts: Optional[Dict[str, str]] = None,
    ):
        self.element_name = element_name
        self.window_name = window_name
        self.attempts = attempts
        self.timeout = timeout
        self.last_error = last_error
        self.artifacts = artifacts or {}
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = [
            f"ElementNotFoundError: element='{self.element_name}' window='{self.window_name}' timeout={self.timeout}s",
        ]
        if self.last_error:
            lines.append(f"Last error: {self.last_error}")
        lines.append("Attempts:")
        for i, a in enumerate(self.attempts, start=1):
            lines.append(f"  {i}. {a.kind}: {a.locator} err={a.error}")
        if self.artifacts:
            lines.append(f"Artifacts: {self.artifacts}")
        return "\n".join(lines)


class ActionError(UIAutoError):
    def __init__(
        self,
        action: str,
        element_name: Optional[str] = None,
        details: Optional[str] = None,
        artifacts: Optional[Dict[str, str]] = None,
        cause: Optional[BaseException] = None,
    ):
        self.action = action
        self.element_name = element_name
        self.details = details
        self.artifacts = artifacts or {}
        self.cause = cause
        super().__init__(self.__str__())

    def __str__(self) -> str:
        base = f"ActionError: action='{self.action}'"
        if self.element_name:
            base += f" element='{self.element_name}'"
        if self.details:
            base += f" details='{self.details}'"
        if self.cause:
            base += f" cause='{type(self.cause).__name__}: {self.cause}'"
        if self.artifacts:
            base += f" artifacts={self.artifacts}"
        return base
