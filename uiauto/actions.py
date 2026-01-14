"""
@file actions.py
@brief Keyword action library for UI automation scenarios.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from pywinauto.keyboard import send_keys

from . exceptions import ActionError
from .resolver import Resolver


class Actions:
    """
    @brief Keyword action library providing high-level UI operations.
    
    All methods resolve element names, perform validation, delegate to Element,
    and wrap errors in ActionError for consistent error handling.
    """

    def __init__(self, resolver:  Resolver):
        """
        @brief Initialize actions library.
        @param resolver Element resolver instance
        """
        self. resolver = resolver

    def click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Click element. 
        @param element Element name from object map
        @param overrides Optional locator overrides
        @throws ActionError if operation fails
        """
        try: 
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.click()
        except Exception as e:
            raise ActionError("click", element_name=element, cause=e)

    def double_click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Double-click element.
        @param element Element name from object map
        @param overrides Optional locator overrides
        @throws ActionError if operation fails
        """
        try:
            el = self. resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.double_click()
        except Exception as e:
            raise ActionError("double_click", element_name=element, cause=e)

    def right_click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Right-click element.
        @param element Element name from object map
        @param overrides Optional locator overrides
        @throws ActionError if operation fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.right_click()
        except Exception as e: 
            raise ActionError("right_click", element_name=element, cause=e)

    def hover(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Hover mouse over element.
        @param element Element name from object map
        @param overrides Optional locator overrides
        @throws ActionError if operation fails
        """
        try: 
            el = self.resolver. resolve(element, overrides=overrides)
            el.wait("visible")
            el.hover()
        except Exception as e:
            raise ActionError("hover", element_name=element, cause=e)

    def type(self, element: str, text:  str, overrides: Optional[Dict[str, Any]] = None, clear: bool = True) -> None:
        """
        @brief Type text into element. 
        @param element Element name from object map
        @param text Text to type
        @param overrides Optional locator overrides
        @param clear Clear existing text before typing
        @throws ActionError if operation fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.set_text(text, clear_first=clear)
        except Exception as e:
            raise ActionError("type", element_name=element, cause=e)

    def wait_for(self, element: str, state: str = "visible", timeout: Optional[float] = None, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Wait for element to reach state.
        @param element Element name from object map
        @param state State to wait for: "exists", "visible", "enabled"
        @param timeout Timeout in seconds
        @param overrides Optional locator overrides
        @throws ActionError if timeout occurs
        """
        try: 
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait(state, timeout=timeout)
        except Exception as e:
            raise ActionError("wait_for", element_name=element, cause=e)

    def assert_state(self, element: str, state: str = "visible", overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Assert element state. 
        @param element Element name from object map
        @param state Expected state: "exists", "visible", "enabled"
        @param overrides Optional locator overrides
        @throws ActionError if assertion fails
        """
        try: 
            el = self.resolver. resolve(element, overrides=overrides)
            if state == "exists" and not el.exists():
                raise AssertionError("Expected exists, but not found")
            if state == "visible" and not (el.exists() and el.is_visible()):
                raise AssertionError("Expected visible, but not visible")
            if state == "enabled" and not (el.exists() and el.is_visible() and el.is_enabled()):
                raise AssertionError("Expected enabled, but not enabled")
        except Exception as e: 
            raise ActionError("assert_state", element_name=element, cause=e)

    def assert_text_equals(self, element: str, expected:  str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Assert element text equals expected value.
        @param element Element name from object map
        @param expected Expected text
        @param overrides Optional locator overrides
        @throws ActionError if assertion fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            actual = el.get_text()
            if actual != expected:
                raise AssertionError(f"Expected '{expected}', got '{actual}'")
        except Exception as e:
            raise ActionError("assert_text_equals", element_name=element, cause=e)

    def assert_text_contains(self, element: str, substring: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Assert element text contains substring.
        @param element Element name from object map
        @param substring Expected substring
        @param overrides Optional locator overrides
        @throws ActionError if assertion fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            actual = el.get_text()
            if substring not in actual:
                raise AssertionError(f"Expected '{substring}' in '{actual}'")
        except Exception as e:
            raise ActionError("assert_text_contains", element_name=element, cause=e)

    def close_window(self, window_name: str) -> None:
        """
        @brief Close window. 
        @param window_name Window name from object map
        @throws ActionError if operation fails
        """
        try:
            w = self.resolver.resolve_window(window_name)
            w.close()
        except Exception as e: 
            raise ActionError("close_window", element_name=window_name, cause=e)

    def hotkey(self, keys: str) -> None:
        """
        @brief Send global hotkey.
        @param keys Key combination (e.g., "^l" for Ctrl+L)
        @throws ActionError if operation fails
        """
        try:
            send_keys(keys, pause=0.05)
        except Exception as e: 
            raise ActionError("hotkey", details=f"keys={keys}", cause=e)

    def set_checkbox(self, element: str, checked: bool, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Set checkbox to specific state.
        @param element Element name from object map
        @param checked True to check, False to uncheck
        @param overrides Optional locator overrides
        @throws ActionError if operation fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")

            try:
                ctrl_type = el.handle. element_info.control_type
                if ctrl_type != "CheckBox":
                    raise ValueError(f"Expected CheckBox, got {ctrl_type}")
            except Exception:
                pass

            if checked:
                el.check()
            else:
                el. uncheck()
        except Exception as e:
            raise ActionError("set_checkbox", element_name=element, cause=e)

    def assert_checkbox_state(self, element: str, checked: bool, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Assert checkbox state. 
        @param element Element name from object map
        @param checked Expected state (True=checked, False=unchecked)
        @param overrides Optional locator overrides
        @throws ActionError if assertion fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            state = el.get_state()
            expected = "checked" if checked else "unchecked"
            if state != expected:
                raise AssertionError(f"Expected {expected}, got {state}")
        except Exception as e:
            raise ActionError("assert_checkbox_state", element_name=element, cause=e)

    def select_combobox(self, element: str, option: str, by_index: bool = False, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Select option in combobox.
        @param element Element name from object map
        @param option Option text or index
        @param by_index True to select by index, False by text
        @param overrides Optional locator overrides
        @throws ActionError if operation fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")

            try:
                ctrl_type = el.handle.element_info.control_type
                if ctrl_type != "ComboBox": 
                    raise ValueError(f"Expected ComboBox, got {ctrl_type}")
            except Exception: 
                pass

            el.select(option, by_index=by_index)
        except Exception as e:
            raise ActionError("select_combobox", element_name=element, cause=e)

    def select_list_item(self, element: str, item_text: str = None, item_index: int = None, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Select item in list. 
        @param element Element name from object map
        @param item_text Item text to select
        @param item_index Item index to select
        @param overrides Optional locator overrides
        @throws ActionError if operation fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            el.select_item(item_text=item_text, item_index=item_index)
        except Exception as e:
            raise ActionError("select_list_item", element_name=element, cause=e)

    def assert_count(self, element: str, expected: int, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        @brief Assert item count in list/combobox.
        @param element Element name from object map
        @param expected Expected item count
        @param overrides Optional locator overrides
        @throws ActionError if assertion fails
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            actual = el.item_count()
            if actual != expected: 
                raise AssertionError(f"Expected {expected} items, got {actual}")
        except Exception as e:
            raise ActionError("assert_count", element_name=element, cause=e)