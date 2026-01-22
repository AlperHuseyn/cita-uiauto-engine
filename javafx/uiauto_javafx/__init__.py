# javafx/uiauto_javafx/__init__.py
"""JavaFX UI automation package using Java Access Bridge."""

from .jab_bridge import JABBridge
from .session import JavaFXSession
from .resolver import JavaFXResolver
from .element import JavaFXElement, ElementMeta
from .actions import JavaFXActions
from .inspector import inspect_window, write_inspect_outputs, emit_elements_yaml

__version__ = "1.0.0"

__all__ = [
    "JABBridge",
    "JavaFXSession",
    "JavaFXResolver",
    "JavaFXElement",
    "ElementMeta",
    "JavaFXActions",
    "inspect_window",
    "write_inspect_outputs",
    "emit_elements_yaml",
]
