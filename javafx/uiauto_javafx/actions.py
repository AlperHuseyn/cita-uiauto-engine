# javafx/uiauto_javafx/actions.py
"""Keyword action library for JavaFX UI automation."""

from __future__ import annotations
from typing import Any, Dict, Optional

from uiauto_core import ActionError

from .resolver import JavaFXResolver


class JavaFXActions:
    """
    Keyword action library for JavaFX automation.
    
    Provides high-level UI operations using Java Access Bridge.
    """
    
    def __init__(self, resolver: JavaFXResolver):
        """
        Initialize actions library.
        
        Args:
            resolver: Element resolver instance
        """
        self.resolver = resolver
    
    def click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Click element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.click()
        except Exception as e:
            raise ActionError("click", element_name=element, cause=e)
    
    def double_click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Double-click element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.double_click()
        except Exception as e:
            raise ActionError("double_click", element_name=element, cause=e)
    
    def right_click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Right-click element (not supported via JAB)."""
        raise ActionError("right_click", element_name=element, 
                         details="Right-click not supported via Java Accessibility API")
    
    def hover(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Hover over element (not supported via JAB)."""
        raise ActionError("hover", element_name=element,
                         details="Hover not supported via Java Accessibility API")
    
    def type(self, element: str, text: str, overrides: Optional[Dict[str, Any]] = None, clear: bool = True) -> None:
        """Type text into element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.set_text(text, clear_first=clear)
        except Exception as e:
            raise ActionError("type", element_name=element, cause=e)
    
    def wait_for(self, element: str, state: str = "visible", timeout: Optional[float] = None, 
                 overrides: Optional[Dict[str, Any]] = None) -> None:
        """Wait for element to reach state."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait(state, timeout=timeout)
        except Exception as e:
            raise ActionError("wait_for", element_name=element, cause=e)
    
    def assert_state(self, element: str, state: str = "visible", overrides: Optional[Dict[str, Any]] = None) -> None:
        """Assert element state."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            if state == "exists" and not el.exists():
                raise AssertionError("Expected exists, but not found")
            if state == "visible" and not (el.exists() and el.is_visible()):
                raise AssertionError("Expected visible, but not visible")
            if state == "enabled" and not (el.exists() and el.is_visible() and el.is_enabled()):
                raise AssertionError("Expected enabled, but not enabled")
        except Exception as e:
            raise ActionError("assert_state", element_name=element, cause=e)
    
    def assert_text_equals(self, element: str, expected: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Assert element text equals expected value."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            actual = el.get_text()
            if actual != expected:
                raise AssertionError(f"Expected '{expected}', got '{actual}'")
        except Exception as e:
            raise ActionError("assert_text_equals", element_name=element, cause=e)
    
    def assert_text_contains(self, element: str, substring: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Assert element text contains substring."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            actual = el.get_text()
            if substring not in actual:
                raise AssertionError(f"Expected '{substring}' in '{actual}'")
        except Exception as e:
            raise ActionError("assert_text_contains", element_name=element, cause=e)
    
    def close_window(self, window_name: str) -> None:
        """Close window."""
        try:
            w = self.resolver.resolve_window(window_name)
            # Dispatch window closing event
            from java.awt.event import WindowEvent
            event = WindowEvent(w, WindowEvent.WINDOW_CLOSING)
            w.dispatchEvent(event)
        except Exception as e:
            raise ActionError("close_window", element_name=window_name, cause=e)
    
    def hotkey(self, keys: str) -> None:
        """Send global hotkey (not supported via JAB)."""
        raise ActionError("hotkey", details=f"keys={keys}",
                         cause=Exception("Hotkey not supported via Java Accessibility API"))
    
    def set_checkbox(self, element: str, checked: bool, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Set checkbox state (basic support)."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            # For checkboxes, we can use AccessibleAction to toggle
            # This is a simplified implementation
            el.click()
        except Exception as e:
            raise ActionError("set_checkbox", element_name=element, cause=e)
    
    def assert_checkbox_state(self, element: str, checked: bool, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Assert checkbox state."""
        raise ActionError("assert_checkbox_state", element_name=element,
                         details="Checkbox state checking not yet implemented for JavaFX")
    
    def select_combobox(self, element: str, option: str, by_index: bool = False, 
                       overrides: Optional[Dict[str, Any]] = None) -> None:
        """Select option in combobox."""
        raise ActionError("select_combobox", element_name=element,
                         details="ComboBox selection not yet implemented for JavaFX")
    
    def select_list_item(self, element: str, item_text: str = None, item_index: int = None,
                        overrides: Optional[Dict[str, Any]] = None) -> None:
        """Select list item."""
        raise ActionError("select_list_item", element_name=element,
                         details="List item selection not yet implemented for JavaFX")
    
    def assert_count(self, element: str, expected: int, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Assert item count."""
        raise ActionError("assert_count", element_name=element,
                         details="Item count assertion not yet implemented for JavaFX")
