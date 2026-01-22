# qtquick/uiauto_qtquick/__init__.py
"""QtQuick UI automation package using pywinauto UIA backend."""

from .session import QtQuickSession
from .resolver import QtQuickResolver
from .element import QtQuickElement, ElementMeta
from .actions import QtQuickActions
from .inspector import inspect_window, write_inspect_outputs, emit_elements_yaml_stateful

__version__ = "1.0.0"

__all__ = [
    "QtQuickSession",
    "QtQuickResolver",
    "QtQuickElement",
    "ElementMeta",
    "QtQuickActions",
    "inspect_window",
    "write_inspect_outputs",
    "emit_elements_yaml_stateful",
]
