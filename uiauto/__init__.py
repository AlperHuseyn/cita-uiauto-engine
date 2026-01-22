# uiauto/__init__.py
"""
DEPRECATED: This package has been split into a monorepo structure.

Please migrate to the new packages:
- uiauto_core: Framework-agnostic engine
- uiauto_qtquick: QtQuick/WPF automation (replaces this package)
- uiauto_javafx: JavaFX automation

Migration example:
    # OLD:
    from uiauto import Repository, Session, Resolver, Actions, Runner
    
    # NEW:
    from uiauto_core import Repository, Runner
    from uiauto_qtquick import QtQuickSession, QtQuickResolver, QtQuickActions

See README.md for full migration guide.
"""
import warnings

warnings.warn(
    "The 'uiauto' package is deprecated. "
    "Please migrate to 'uiauto_core' + 'uiauto_qtquick' or 'uiauto_javafx'. "
    "See README.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)

from .repository import Repository
from .session import Session
from .resolver import Resolver
from .actions import Actions
from .runner import Runner

__all__ = ["Repository", "Session", "Resolver", "Actions", "Runner"]
