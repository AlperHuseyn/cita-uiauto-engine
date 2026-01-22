# core/uiauto_core/__init__.py
"""Framework-agnostic UI automation core."""

from .repository import Repository, AppConfig
from .runner import Runner
from .waits import wait_until
from .exceptions import (
    UIAutoError,
    ConfigError,
    TimeoutError,
    WindowNotFoundError,
    ElementNotFoundError,
    ActionError,
    LocatorAttempt,
)
from .interfaces import ISession, IResolver, IElement
from .artifacts import make_artifacts, ensure_dir

__version__ = "1.0.0"

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
    "IResolver",
    "IElement",
    "make_artifacts",
    "ensure_dir",
]
