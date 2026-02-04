# uiauto/__init__.py
"""
cita-uiauto-engine - Production-ready Windows UI automation framework.

Quick Start:
    from uiauto import Repository, Session, Resolver, Actions
    
    repo = Repository.load("elements.yaml")
    session = Session(backend="uia")
    resolver = Resolver(session, repo)
    actions = Actions(resolver)
    
    actions.click("login_button")
"""

__version__ = "1.2.0"

# Core classes
from .repository import Repository
from .session import Session
from .resolver import Resolver
from .actions import Actions
from .runner import Runner

# Element classes
from .element import Element, ElementMeta

# Configuration
from .config import (
    TimeConfig,
    TimeoutSettings,
    configure_for_ci,
    configure_for_local_dev,
)

# Context tracking
from .context import (
    ActionContext,
    ActionContextManager,
    tracked_action,
)

# Wait utilities
from .waits import (
    wait_until,
    wait_until_passes,
    wait_until_not,
    wait_for_any,
    retry,
)

# Exceptions
from .exceptions import (
    UIAutoError,
    ConfigError,
    TimeoutError,
    WindowNotFoundError,
    ElementNotFoundError,
    ElementNotVisibleError,
    ElementNotEnabledError,
    StaleElementError,
    ActionError,
    LocatorAttempt,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "Repository",
    "Session",
    "Resolver",
    "Actions",
    "Runner",
    # Elements
    "Element",
    "ElementMeta",
    # Configuration
    "TimeConfig",
    "TimeoutSettings",
    "configure_for_ci",
    "configure_for_local_dev",
    # Context
    "ActionContext",
    "ActionContextManager",
    "tracked_action",
    # Waits
    "wait_until",
    "wait_until_passes",
    "wait_until_not",
    "wait_for_any",
    "retry",
    # Exceptions
    "UIAutoError",
    "ConfigError",
    "TimeoutError",
    "WindowNotFoundError",
    "ElementNotFoundError",
    "ElementNotVisibleError",
    "ElementNotEnabledError",
    "StaleElementError",
    "ActionError",
    "LocatorAttempt",
]