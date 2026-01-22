# qtquick/uiauto_qtquick/__init__.py
"""
UIAuto QtQuick - QtQuick UI automation using pywinauto UIA backend.

This package provides QtQuick-specific implementation of the UIAuto framework,
supporting QtQuick/QML applications on Windows via Microsoft UI Automation.
"""

from uiauto_qtquick.session import QtQuickSession
from uiauto_qtquick.resolver import QtQuickResolver
from uiauto_qtquick.element import QtQuickElement
from uiauto_qtquick.actions import QtQuickActions

__all__ = [
    "QtQuickSession",
    "QtQuickResolver",
    "QtQuickElement",
    "QtQuickActions",
]

__version__ = "1.0.0"
