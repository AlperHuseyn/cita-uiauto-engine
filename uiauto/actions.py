# uiauto/actions.py
"""
@file actions.py
@brief Keyword action library for UI automation scenarios.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from pywinauto.keyboard import send_keys

from .context import ActionContextManager, tracked_action
from .exceptions import ActionError
from .resolver import Resolver
from .waits import wait_for_any


class Actions:
    """
    Keyword action library providing high-level UI operations.
    
    All methods resolve element names, perform validation, delegate to Element,
    and wrap errors in ActionError for consistent error handling.
    """

    def __init__(self, resolver: Resolver):
        """
        @param resolver Element resolver instance
        """
        self.resolver = resolver

    @tracked_action("click")
    def click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Click element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.click()
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("click", element_name=element, cause=e) from e

    @tracked_action("double_click")
    def double_click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Double-click element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.double_click()
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("double_click", element_name=element, cause=e) from e

    @tracked_action("right_click")
    def right_click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Right-click element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.right_click()
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("right_click", element_name=element, cause=e) from e

    @tracked_action("hover")
    def hover(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Hover mouse over element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            el.hover()
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("hover", element_name=element, cause=e) from e

    @tracked_action("type")
    def type(
        self,
        element: str,
        text: str,
        overrides: Optional[Dict[str, Any]] = None,
        clear: bool = True
    ) -> None:
        """Type text into element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.set_text(text, clear_first=clear)
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("type", element_name=element, cause=e) from e

    @tracked_action("click_and_type")
    def click_and_type(
        self,
        element: str,
        text: str,
        clear: bool = True,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Click an element and type text into it in one step.
        
        Useful for text fields that need to be focused before typing.
        
        @param element Element name from object map
        @param text Text to type
        @param clear Clear existing text before typing
        @param overrides Optional locator overrides
        @throws ActionError if operation fails
        """
        with ActionContextManager.action("click_and_type", element_name=element):
            try:
                el = self.resolver.resolve(element, overrides=overrides)
                el.wait("enabled")
                el.click()
                
                # Brief pause to ensure focus
                import time
                time.sleep(0.1)
                
                el.set_text(text, clear_first=clear)
                
            except ActionError:
                raise
            except Exception as e:
                raise ActionError("click_and_type", element_name=element, cause=e) from e

    @tracked_action("wait_for")
    def wait_for(
        self,
        element: str,
        state: str = "visible",
        timeout: Optional[float] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Wait for element to reach state."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait(state, timeout=timeout)
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("wait_for", element_name=element, cause=e) from e

    def wait_for_any(
        self,
        elements: List[str],
        timeout: Optional[float] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Wait for any of the specified elements to appear."""
        effective_timeout = timeout if timeout is not None else self.resolver.timeout
        
        predicates = [
            lambda name=name: self.resolver.exists(name, timeout=0, overrides=overrides)
            for name in elements
        ]
        
        try:
            result_index = wait_for_any(
                predicates,
                timeout=effective_timeout,
                interval=self.resolver.interval,
                descriptions=elements
            )
            return elements[result_index]
        except Exception as e:
            raise ActionError("wait_for_any", details=f"elements={elements}", cause=e) from e

    def wait_for_gone(
        self,
        element: str,
        timeout: Optional[float] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Wait for an element to disappear."""
        try:
            self.resolver.wait_for_element_gone(element, timeout=timeout, overrides=overrides)
        except Exception as e:
            raise ActionError("wait_for_gone", element_name=element, cause=e) from e

    @tracked_action("assert_state")
    def assert_state(
        self,
        element: str,
        state: str = "visible",
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Assert element state."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            if state == "exists" and not el.exists():
                raise AssertionError("Expected exists, but not found")
            if state == "visible" and not (el.exists() and el.is_visible()):
                raise AssertionError("Expected visible, but not visible")
            if state == "enabled" and not (el.exists() and el.is_visible() and el.is_enabled()):
                raise AssertionError("Expected enabled, but not enabled")
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("assert_state", element_name=element, cause=e) from e

    @tracked_action("assert_text_equals")
    def assert_text_equals(
        self,
        element: str,
        expected: str,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Assert element text equals expected value."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            actual = el.get_text()
            if actual != expected:
                raise AssertionError(f"Expected '{expected}', got '{actual}'")
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("assert_text_equals", element_name=element, cause=e) from e

    @tracked_action("assert_text_contains")
    def assert_text_contains(
        self,
        element: str,
        substring: str,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Assert element text contains substring."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            actual = el.get_text()
            if substring not in actual:
                raise AssertionError(f"Expected '{substring}' in '{actual}'")
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("assert_text_contains", element_name=element, cause=e) from e

    @tracked_action("close_window")
    def close_window(self, window_name: str) -> None:
        """Close window."""
        try:
            w = self.resolver.resolve_window(window_name)
            w.close()
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("close_window", element_name=window_name, cause=e) from e

    def hotkey(self, keys: str) -> None:
        """Send global hotkey."""
        with ActionContextManager.action("hotkey", metadata={"keys": keys}):
            try:
                send_keys(keys, pause=0.05)
            except Exception as e:
                raise ActionError("hotkey", details=f"keys={keys}", cause=e) from e

    @tracked_action("set_checkbox")
    def set_checkbox(
        self,
        element: str,
        checked: bool,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set checkbox to specific state."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")

            try:
                ctrl_type = el.handle.element_info.control_type
                if ctrl_type != "CheckBox":
                    raise ValueError(f"Expected CheckBox, got {ctrl_type}")
            except Exception:
                pass

            if checked:
                el.check()
            else:
                el.uncheck()
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("set_checkbox", element_name=element, cause=e) from e

    @tracked_action("assert_checkbox_state")
    def assert_checkbox_state(
        self,
        element: str,
        checked: bool,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Assert checkbox state."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            state = el.get_state()
            expected = "checked" if checked else "unchecked"
            if state != expected:
                raise AssertionError(f"Expected {expected}, got {state}")
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("assert_checkbox_state", element_name=element, cause=e) from e

    @tracked_action("select_combobox")
    def select_combobox(
        self,
        element: str,
        option: str,
        by_index: bool = False,
        item_element: Optional[str] = None,  # NEW: for QtQuick
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Select option in combobox.
        
        For QtQuick ComboBoxes, provide item_element to click the ListItem directly.
        """
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")

            # Check if it's a ComboBox
            try:
                ctrl_type = el.handle.element_info.control_type
                if ctrl_type != "ComboBox":
                    raise ValueError(f"Expected ComboBox, got {ctrl_type}")
            except Exception:
                pass

            # Try 1: If item_element is provided, use click-based selection (QtQuick)
            if item_element:
                el.click()
                import time
                time.sleep(0.2)
                item = self.resolver.resolve(item_element, overrides=overrides)
                item.wait("visible")
                item.click()
                return

            # Try 2: Standard pywinauto select()
            try:
                el.select(option, by_index=by_index)
                return
            except Exception as select_error:
                # Try 3: Fallback - try to find and click a matching ListItem
                try:
                    el.click()  # Open dropdown
                    import time
                    time.sleep(0.2)
                    
                    # Try to find the item by option text
                    item = self.resolver.resolve(
                        option.lower(),  # Assumes element name matches option
                        overrides=overrides
                    )
                    item.wait("visible")
                    item.click()
                    return
                except Exception:
                    # Re-raise original error if fallback also fails
                    raise select_error

        except ActionError:
            raise
        except Exception as e:
            raise ActionError("select_combobox", element_name=element, cause=e) from e

    @tracked_action("select_combobox_item")
    def select_combobox_item(
        self,
        combobox_element: str,
        item_element: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Select an item in a QtQuick ComboBox by clicking the combobox,
        then clicking the list item.
        
        @param combobox_element ComboBox element name
        @param item_element ListItem element name to select
        @param overrides Optional locator overrides
        """
        try:
            combo = self.resolver.resolve(combobox_element, overrides=overrides)
            combo.wait("enabled")
            combo.click()
            
            import time
            time.sleep(0.2)
            
            item = self.resolver.resolve(item_element, overrides=overrides)
            item.wait("visible")
            item.click()
            
        except ActionError:
            raise
        except Exception as e:
            raise ActionError(
                "select_combobox_item",
                element_name=f"{combobox_element} -> {item_element}",
                cause=e
            ) from e

    @tracked_action("select_list_item")
    def select_list_item(
        self,
        element: str,
        item_text: Optional[str] = None,
        item_index: Optional[int] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Select item in list."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            el.select_item(item_text=item_text, item_index=item_index)
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("select_list_item", element_name=element, cause=e) from e

    @tracked_action("assert_count")
    def assert_count(
        self,
        element: str,
        expected: int,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Assert item count in list/combobox."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            actual = el.item_count()
            if actual != expected:
                raise AssertionError(f"Expected {expected} items, got {actual}")
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("assert_count", element_name=element, cause=e) from e
    
    # --- New Enhanced Methods ---
    
    def click_if_exists(
        self,
        element: str,
        timeout: float = 2.0,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Click an element if it exists, otherwise continue."""
        try:
            el = self.resolver.resolve(element, overrides=overrides, timeout=timeout)
            el.wait("enabled", timeout=timeout)
            el.click()
            return True
        except Exception:
            return False
    
    def get_text(
        self,
        element: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get text content of an element."""
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("visible")
            return el.get_text()
        except ActionError:
            raise
        except Exception as e:
            raise ActionError("get_text", element_name=element, cause=e) from e
    
    def exists(
        self,
        element: str,
        timeout: float = 0,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if an element exists."""
        return self.resolver.exists(element, timeout=timeout, overrides=overrides)