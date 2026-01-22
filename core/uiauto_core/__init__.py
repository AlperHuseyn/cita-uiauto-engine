# core/uiauto_core/__init__.py
"""
UIAuto Core - Framework-agnostic UI automation engine.

This package provides the core functionality for UI automation including:
- Repository: YAML object map loading and validation
- Runner: Scenario execution engine
- Waits: Retry/polling utilities
- Exceptions: Common exception types
- Artifacts: Screenshot and report generation utilities
- Interfaces: Abstract base classes for framework implementations
"""

from uiauto_core.repository import Repository, AppConfig
from uiauto_core.runner import Runner
from uiauto_core.waits import wait_until
from uiauto_core.exceptions import (
    UIAutoError,
    ConfigError,
    TimeoutError,
    WindowNotFoundError,
    ElementNotFoundError,
    ActionError,
    LocatorAttempt,
)
from uiauto_core.interfaces import ISession, IElement, IResolver
from uiauto_core import artifacts

__all__ = [
    "Repository",
    "AppConfig",
    "Runner",
    "wait_until",
    "UIAutoError",
    "ConfigError",
    "TimeoutError",
    "WindowNotFoundError",
    "ElementNotFoundError",
    "ActionError",
    "LocatorAttempt",
    "ISession",
    "IElement",
    "IResolver",
    "artifacts",
]

__version__ = "1.0.0"
