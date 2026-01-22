"""
uiauto_qtquick - QtQuick/UIA automation framework.

Provides QtQuick/Windows UIA-specific implementation of uiauto_core interfaces
using pywinauto.
"""

from .session import QtQuickSession
from .resolver import QtQuickResolver
from .element import QtQuickElement, ElementMeta
from .actions import QtQuickActions
from .inspector import QtQuickInspector

__version__ = "1.0.0"

__all__ = [
    "QtQuickSession",
    "QtQuickResolver",
    "QtQuickElement",
    "ElementMeta",
    "QtQuickActions",
    "QtQuickInspector",
]
