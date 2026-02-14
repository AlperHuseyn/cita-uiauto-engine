# uiauto/exceptions.py
"""
@file exceptions.py
@brief Custom exception classes for UI automation framework.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class UIAutoError(Exception):
    """Base exception for the framework."""
    pass


class ConfigError(UIAutoError):
    """Raised when YAML/JSON configuration is invalid."""
    pass


class TimeoutError(UIAutoError):
    """
    Raised when a wait/retry times out.
    
    This exception preserves the original exception that caused the timeout,
    making debugging significantly easier.
    
    Attributes:
        original_exception: The last exception that was raised before timeout
        description: Human-readable description of what was being waited for
        timeout: The timeout value in seconds
        attempt_count: Number of attempts made (if applicable)
        elapsed_time: Actual elapsed time in seconds (if applicable)
    """
    
    def __init__(self, message: str):
        super().__init__(message)
        self.original_exception: Optional[BaseException] = None
        self.description: Optional[str] = None
        self.timeout: Optional[float] = None
        self.attempt_count: Optional[int] = None
        self.elapsed_time: Optional[float] = None
        self.stage: Optional[str] = None
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        
        details = []
        if self.original_exception is not None:
            details.append(f"Original exception: {type(self.original_exception).__name__}")
        if self.attempt_count is not None:
            details.append(f"Attempts: {self.attempt_count}")
        if self.elapsed_time is not None:
            details.append(f"Elapsed: {self.elapsed_time:.2f}s")
        if self.stage is not None:
            details.append(f"Stage: {self.stage}")

        
        if details:
            return f"{base_msg} [{', '.join(details)}]"
        return base_msg
    
    def get_root_cause(self) -> Optional[BaseException]:
        """
        Get the root cause exception by traversing the chain.
        
        @return The deepest original_exception in the chain, or None
        """
        current = self.original_exception
        while current is not None:
            if hasattr(current, 'original_exception') and current.original_exception is not None:
                current = current.original_exception
            else:
                return current
        return None
    
    def get_traceback_str(self) -> str:
        """
        Get a formatted traceback string from the original exception.
        
        @return Formatted traceback string or empty string if no original exception
        """
        if self.original_exception is None:
            return ""
        
        import traceback
        return "".join(traceback.format_exception(
            type(self.original_exception),
            self.original_exception,
            self.original_exception.__traceback__
        ))


@dataclass
class LocatorAttempt:
    """Records a single locator attempt for debugging."""
    kind: str
    locator: Dict[str, Any]
    error: Optional[str] = None


class WindowNotFoundError(UIAutoError):
    """
    Raised when a window cannot be found within the timeout period.
    
    Contains detailed information about all locator attempts made.
    """
    
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
    """
    Raised when an element cannot be found within the timeout period.
    
    Contains detailed information about all locator attempts made,
    including which window was searched.
    """
    
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
            f"ElementNotFoundError: element='{self.element_name}' "
            f"window='{self.window_name}' timeout={self.timeout}s",
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
    """
    Raised when a UI action fails.
    
    Contains information about the action, target element,
    and the underlying cause.
    """
    
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
    
    def get_cause_traceback(self) -> str:
        """
        Get a formatted traceback string from the cause exception.
        
        @return Formatted traceback string or empty string if no cause
        """
        if self.cause is None:
            return ""
        
        import traceback
        return "".join(traceback.format_exception(
            type(self.cause),
            self.cause,
            self.cause.__traceback__
        ))


class ElementNotVisibleError(UIAutoError):
    """Raised when an element exists but is not visible."""
    
    def __init__(self, element_name: str, message: Optional[str] = None):
        self.element_name = element_name
        msg = f"Element '{element_name}' is not visible"
        if message:
            msg += f": {message}"
        super().__init__(msg)


class ElementNotEnabledError(UIAutoError):
    """Raised when an element exists and is visible but not enabled."""
    
    def __init__(self, element_name: str, message: Optional[str] = None):
        self.element_name = element_name
        msg = f"Element '{element_name}' is not enabled"
        if message:
            msg += f": {message}"
        super().__init__(msg)


class StaleElementError(UIAutoError):
    """Raised when a cached element reference is no longer valid."""
    
    def __init__(self, element_name: str, message: Optional[str] = None):
        self.element_name = element_name
        msg = f"Element '{element_name}' is stale (no longer attached to DOM)"
        if message:
            msg += f": {message}"
        super().__init__(msg)
