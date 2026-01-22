"""
uiauto_core - Framework-agnostic UI automation core.

Provides interfaces, repository, runner, and utilities for building
UI automation frameworks.
"""

from .interfaces import ISession, IResolver, IElement, IInspector, IActions
from .repository import Repository
from .runner import Runner
from .waits import wait_until
from .exceptions import (
    UIAutoError,
    ConfigError,
    WindowNotFoundError,
    ElementNotFoundError,
    ActionError,
)

__version__ = "1.0.0"

__all__ = [
    # Interfaces
    "ISession",
    "IResolver",
    "IElement",
    "IInspector",
    "IActions",
    # Core classes
    "Repository",
    "Runner",
    # Utilities
    "wait_until",
    # Exceptions
    "UIAutoError",
    "ConfigError",
    "WindowNotFoundError",
    "ElementNotFoundError",
    "ActionError",
]
