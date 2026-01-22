"""
@file element.py
@brief Robust element wrapper with fallback strategies for UI automation. 
QtQuick-specific implementation using pywinauto.
"""

from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

from uiauto_core.waits import wait_until
from uiauto_core.interfaces import IElement


@dataclass
class ElementMeta:
    """
    @brief Metadata for resolved UI element.
    """
    name: str
    window_name: str
    used_locator: Dict[str, Any]
    found_via_name: bool = False


class QtQuickElement(IElement):
    """
    @brief Robust wrapper around pywinauto element handle.
    
    Provides framework-specific helpers and implements fallback strategies
    for reliable cross-platform UI automation (Win32, WPF, UIA, QtQuick).
    """

    def __init__(self, handle, meta: ElementMeta, default_timeout: float, polling_interval: float):
        """
        @brief Initialize element wrapper.
        @param handle Pywinauto element wrapper (ButtonWrapper, EditWrapper, etc.)
        @param meta Element metadata
        @param default_timeout Default timeout for wait operations (seconds)
        @param polling_interval Polling interval for wait operations (seconds)
        """
        self. handle = handle
        self.meta = meta
        self.default_timeout = default_timeout
        self.polling_interval = polling_interval

    def exists(self) -> bool:
        """
        @brief Check if element exists in UI tree.
        @return True if element exists, False otherwise
        @note For QtQuick elements found via name/name_re, always returns True
        """
        if self.meta.found_via_name:
            return True
        try:
            return bool(self.handle.exists())
        except Exception:
            return False

    def is_visible(self) -> bool:
        """
        @brief Check if element is visible.
        @return True if visible, False otherwise
        @note Also checks for zero-size rectangles (effectively invisible)
        """
        try:
            if not self.handle.is_visible():
                return False
            try:
                rect = self.handle.rectangle()
                if rect.width() == 0 or rect.height() == 0:
                    return False
            except Exception:
                pass
            return True
        except Exception:
            return False

    def is_enabled(self) -> bool:
        """
        @brief Check if element is enabled.
        @return True if enabled, False otherwise
        @note For Edit controls, read-only state counts as disabled
        """
        try: 
            if not self.handle.is_enabled():
                return False
            try:
                ctrl_type = self.handle.element_info.control_type
                if ctrl_type == "Edit": 
                    if hasattr(self.handle, 'is_read_only') and self.handle.is_read_only():
                        return False
            except Exception:
                pass
            return True
        except Exception: 
            return False

    def wait(self, state: str = "exists", timeout: Optional[float] = None) -> "QtQuickElement":
        """
        @brief Wait for element to reach specified state.
        @param state State to wait for:  "exists", "visible", "enabled"
        @param timeout Timeout in seconds (uses default_timeout if None)
        @return Self for chaining
        @throws TimeoutError if state not reached within timeout
        """
        timeout = self.default_timeout if timeout is None else float(timeout)

        def pred():
            if state == "exists":
                return self.exists()
            if state == "visible":
                return self.exists() and self.is_visible()
            if state == "enabled": 
                return self.exists() and self.is_visible() and self.is_enabled()
            raise ValueError(f"Unknown wait state: {state}")

        wait_until(pred, timeout=timeout, interval=self.polling_interval,
                   description=f"{self.meta.name} to be {state}")
        return self

    def click(self, ensure_visible: bool = True, retry_count: int = 2) -> None:
        """
        @brief Robust click with automatic scroll and retry.
        @param ensure_visible Scroll into view if not visible
        @param retry_count Number of retry attempts on failure
        @throws RuntimeError if click fails after all retries
        """
        for attempt in range(retry_count):
            try:
                if ensure_visible and not self.is_visible():
                    self.scroll_into_view()
                self.handle.click_input()
                return
            except Exception as e:
                if attempt == retry_count - 1:
                    raise RuntimeError(f"Click failed on {self.meta.name}: {e}")
                time.sleep(0.2)

    def double_click(self, ensure_visible: bool = True) -> None:
        """
        @brief Robust double-click with fallback.
        @param ensure_visible Scroll into view if not visible
        @throws RuntimeError if double-click fails
        """
        if ensure_visible and not self.is_visible():
            self.scroll_into_view()

        try:
            self.handle.double_click_input()
            return
        except Exception: 
            pass

        try:
            self. handle.click_input()
            time.sleep(0.05)
            self.handle.click_input()
        except Exception as e:
            raise RuntimeError(f"Double-click failed on {self.meta.name}: {e}")

    def right_click(self, ensure_visible: bool = True) -> None:
        """
        @brief Robust right-click with fallback.
        @param ensure_visible Scroll into view if not visible
        @throws RuntimeError if right-click fails
        """
        if ensure_visible and not self.is_visible():
            self.scroll_into_view()

        try:
            self.handle.right_click_input()
            return
        except Exception:
            pass

        try: 
            self.handle.click_input(button='right')
        except Exception as e:
            raise RuntimeError(f"Right-click failed on {self.meta.name}: {e}")

    def hover(self) -> None:
        """
        @brief Move mouse cursor over element center.
        @throws RuntimeError if hover fails
        """
        try:
            rect = self.handle.rectangle()
            center_x = (rect.left + rect.right) // 2
            center_y = (rect.top + rect.bottom) // 2

            from pywinauto import mouse
            mouse.move(coords=(center_x, center_y))
        except Exception as e: 
            raise RuntimeError(f"Hover failed on {self.meta.name}: {e}")

    def set_text(self, text: str, clear_first: bool = False) -> None:
        """
        @brief Robust text setting with multiple fallback strategies.
        @param text Text to set
        @param clear_first Clear existing text before setting
        @throws RuntimeError if all strategies fail
        """
        if clear_first:
            try:
                self.clear()
            except Exception:
                pass

        try:
            self.handle.set_edit_text(text)
            return
        except Exception:
            pass

        try:
            self.handle.set_text(text)
            return
        except Exception: 
            pass

        try: 
            self.focus()
            self.handle.type_keys(text, with_spaces=True, set_foreground=True)
            return
        except Exception as e:
            raise RuntimeError(f"Set text failed on {self.meta. name}: {e}")

    def type_keys(self, keys: str, with_spaces: bool = True, pause: float = 0.05) -> None:
        """
        @brief Robust keyboard input with focus handling.
        @param keys Keys to send (pywinauto format)
        @param with_spaces Allow spaces in key sequences
        @param pause Pause between keystrokes (seconds)
        @throws RuntimeError if typing fails
        """
        try: 
            self.focus()
        except Exception:
            pass

        try:
            self.handle. type_keys(keys, with_spaces=with_spaces, set_foreground=True, pause=pause)
            return
        except Exception: 
            pass

        try: 
            from pywinauto.keyboard import send_keys
            self.focus()
            send_keys(keys, pause=pause)
        except Exception as e:
            raise RuntimeError(f"Type keys failed on {self.meta.name}:  {e}")

    def focus(self) -> None:
        """
        @brief Robust focus setting with multiple strategies.
        @throws RuntimeError if all focus strategies fail
        """
        try:
            self.handle.set_focus()
            return
        except Exception:
            pass

        try:
            self.handle. click_input()
            return
        except Exception:
            pass

        try:
            parent = self.handle.parent()
            parent.set_focus()
            self.handle.set_focus()
        except Exception as e:
            raise RuntimeError(f"Focus failed on {self.meta.name}: {e}")

    def clear(self) -> None:
        """
        @brief Clear text from control with multiple strategies.
        @throws RuntimeError if all clear strategies fail
        """
        try:
            self.focus()
            self.handle.type_keys("^a{DELETE}")
            return
        except Exception: 
            pass

        try: 
            self.handle.set_edit_text("")
            return
        except Exception:
            pass

        try:
            self. handle.set_text("")
        except Exception as e:
            raise RuntimeError(f"Clear failed on {self. meta.name}: {e}")

    def get_text(self) -> str:
        """
        @brief Robust text retrieval with multiple strategies.
        @return Element text or empty string if retrieval fails
        """
        try:
            texts = self.handle.texts()
            if texts:
                return texts[0]
        except Exception:
            pass

        try:
            return self.handle.window_text()
        except Exception: 
            pass

        try: 
            return self.handle.get_value()
        except Exception:
            pass

        return ""

    def scroll_into_view(self) -> None:
        """
        @brief Scroll element into viewport if supported.
        @note Best-effort operation, silently fails if not supported
        """
        try: 
            self.handle.scroll_into_view()
        except Exception: 
            pass

    def check(self) -> None:
        """
        @brief Ensure checkbox is checked (idempotent).
        @note Works with UIA TogglePattern, Win32 checkboxes, and click fallback
        """
        try: 
            current_state = self.handle.get_toggle_state()
            if current_state != 1:
                self.handle.toggle()
            return
        except AttributeError:
            pass

        try:
            self.handle. check()
            return
        except AttributeError:
            pass

        try:
            current = self.handle.get_check_state()
            if current != 1:
                self.click()
            return
        except Exception:
            pass

        self.click()

    def uncheck(self) -> None:
        """
        @brief Ensure checkbox is unchecked (idempotent).
        @note Works with UIA TogglePattern, Win32 checkboxes, and click fallback
        """
        try:
            current_state = self.handle.get_toggle_state()
            if current_state != 0:
                self. handle.toggle()
            return
        except AttributeError:
            pass

        try:
            self.handle.uncheck()
            return
        except AttributeError: 
            pass

        try: 
            current = self.handle.get_check_state()
            if current != 0:
                self.click()
            return
        except Exception:
            pass

        self.click()

    def toggle(self) -> None:
        """
        @brief Toggle checkbox state.
        """
        try:
            self. handle.toggle()
        except AttributeError:
            self.click()

    def get_state(self) -> str:
        """
        @brief Get checkbox state.
        @return "checked", "unchecked", "indeterminate", or "unknown"
        """
        try:
            state = self.handle.get_toggle_state()
            return {0: "unchecked", 1: "checked", 2: "indeterminate"}.get(state, "unknown")
        except AttributeError: 
            pass

        try:
            state = self.handle.get_check_state()
            return {0: "unchecked", 1: "checked", 2: "indeterminate"}.get(state, "unknown")
        except Exception:
            return "unknown"

    def select(self, option, by_index:  bool = False) -> None:
        """
        @brief Robust selection for ComboBox/ListBox with multiple strategies.
        @param option Option text or index to select
        @param by_index True to select by index, False to select by text
        @throws RuntimeError if all selection strategies fail
        """
        try:
            if by_index:
                self. handle.select(int(option))
            else:
                self.handle.select(option)
            return
        except Exception:
            pass

        try:
            self.handle.expand()
            time.sleep(0.2)
            items = self.handle.descendants(control_type="ListItem")
            for item in items:
                try:
                    if str(option) in item.window_text():
                        item.click_input()
                        return
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self.focus()
            self.clear()
            self.type_keys(str(option))
            self.type_keys("{ENTER}")
            return
        except Exception: 
            pass

        raise RuntimeError(f"Select failed on {self.meta.name} for option '{option}'")

    def expand(self) -> None:
        """
        @brief Expand ComboBox dropdown. 
        """
        try:
            self. handle.expand()
        except AttributeError:
            self.click()

    def collapse(self) -> None:
        """
        @brief Collapse ComboBox dropdown.
        """
        try:
            self.handle. collapse()
        except AttributeError:
            self.type_keys("{ESC}")

    def item_texts(self) -> List[str]:
        """
        @brief Get all item texts from ComboBox/ListBox.
        @return List of item texts
        """
        try:
            return self.handle.item_texts()
        except Exception:
            pass

        try: 
            items = self.handle.descendants(control_type="ListItem")
            return [item.window_text() for item in items]
        except Exception:
            return []

    def select_item(self, item_text: str = None, item_index: int = None) -> None:
        """
        @brief Robust item selection for ListBox/ListView.
        @param item_text Item text to select
        @param item_index Item index to select
        @throws RuntimeError if selection fails
        """
        if item_index is not None:
            try:
                self.handle.select(item_index)
                return
            except Exception:
                pass

        if item_text is not None: 
            try:
                self.handle.select(item_text)
                return
            except Exception:
                pass

        if item_text is not None:
            try:
                items = self.handle.descendants(control_type="ListItem")
                for item in items:
                    if item_text in item.window_text():
                        item.click_input()
                        return
            except Exception:
                pass

        raise RuntimeError(f"Select item failed on {self.meta.name}")

    def item_count(self) -> int:
        """
        @brief Get item count in list/combobox.
        @return Number of items
        """
        try:
            return self.handle. item_count()
        except Exception:
            pass

        try: 
            items = self.handle.descendants(control_type="ListItem")
            return len(items)
        except Exception:
            return 0

    def __getattr__(self, name: str):
        """
        @brief Delegate unknown methods to pywinauto handle.
        @param name Method name
        @return Method from handle
        @throws AttributeError if method not found
        """
        if hasattr(self.handle, name):
            return getattr(self. handle, name)
        raise AttributeError(
            f"'{type(self).__name__}' and its handle have no attribute '{name}'"
        )