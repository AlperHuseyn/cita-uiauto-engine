# javafx/uiauto_javafx/__init__.py
"""
UIAuto JavaFX - JavaFX UI automation using Java Access Bridge.

This package provides JavaFX-specific implementation of the UIAuto framework,
supporting JavaFX applications via the Java Accessibility API.
"""

from uiauto_javafx.session import JavaFXSession
from uiauto_javafx.resolver import JavaFXResolver
from uiauto_javafx.element import JavaFXElement
from uiauto_javafx.actions import JavaFXActions

__all__ = [
    "JavaFXSession",
    "JavaFXResolver",
    "JavaFXElement",
    "JavaFXActions",
]

__version__ = "1.0.0"
