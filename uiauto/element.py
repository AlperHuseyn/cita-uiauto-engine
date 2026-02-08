# uiauto/element.py
"""
@file element.py
@brief Element wrapper with wait and action capabilities.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

from .waits import wait_until
from .config import TimeConfig
from .context import ActionContextManager

if TYPE_CHECKING:
    pass


@dataclass
class ElementMeta:
    """
    Metadata about how an element was found.
    Used for debugging and error reporting.
    """
    name: str
    window_name: str
    used_locator: Dict[str, Any] = field(default_factory=dict)
    found_via_name: bool = False


class Element:
    """
    Element wrapper providing high-level operations on UI elements.
    
    This class wraps a raw pywinauto element and provides:
    - State queries (exists, is_visible, is_enabled)
    - Wait operations
    - Click, type, and other actions
    - Rich metadata for debugging
    """
    
    def __init__(
        self,
        handle: Any,
        meta: Optional[ElementMeta] = None,
        default_timeout: float = 10.0,
        polling_interval: float = 0.2,
    ):
        """
        @param handle Raw pywinauto element wrapper
        @param meta Element metadata for debugging
        @param default_timeout Default timeout for wait operations
        @param polling_interval Polling interval for waits
        """
        self._handle = handle
        self._meta = meta or ElementMeta(name="unknown", window_name="unknown")
        self._default_timeout = default_timeout
        self._polling_interval = polling_interval
    
    @property
    def handle(self) -> Any:
        """Get the underlying pywinauto element."""
        return self._handle
    
    @property
    def meta(self) -> ElementMeta:
        """Get element metadata."""
        return self._meta
    
    @property
    def name(self) -> str:
        """Get element name."""
        return self._meta.name
    
    @property
    def window_name(self) -> str:
        """Get parent window name."""
        return self._meta.window_name
    
    # --- State Queries ---
    
    def exists(self) -> bool:
        """Check if element exists in the UI tree."""
        try:
            if hasattr(self._handle, 'exists'):
                return bool(self._handle.exists())
            return True
        except Exception:
            return False
    
    def is_visible(self) -> bool:
        """Check if element is visible."""
        try:
            if hasattr(self._handle, 'is_visible'):
                return bool(self._handle.is_visible())
            return True
        except Exception:
            return False
    
    def is_enabled(self) -> bool:
        """Check if element is enabled."""
        try:
            if hasattr(self._handle, 'is_enabled'):
                return bool(self._handle.is_enabled())
            return True
        except Exception:
            return False
    
    # --- Wait Operations ---
    
    def wait(self, state: str = "exists", timeout: Optional[float] = None) -> Element:
        """
        Wait for element to reach a specific state.
        
        @param state One of: "exists", "visible", "enabled"
        @param timeout Override timeout
        @return self for chaining
        """
        if state == "exists":
            config = TimeConfig.current().element_wait
        elif state == "visible":
            config = TimeConfig.current().visibility_wait
        elif state == "enabled":
            config = TimeConfig.current().enabled_wait
        else:
            raise ValueError(f"Unknown state: {state}. Use 'exists', 'visible', or 'enabled'")

        effective_timeout = timeout if timeout is not None else config.timeout
        effective_interval = config.interval
        
        if state == "exists":
            wait_until(
                self.exists,
                timeout=effective_timeout,
                interval=effective_interval,
                description=f"element '{self._meta.name}' to exist"
            )
        elif state == "visible":
            wait_until(
                lambda: self.exists() and self.is_visible(),
                timeout=effective_timeout,
                interval=effective_interval,
                description=f"element '{self._meta.name}' to be visible"
            )
        elif state == "enabled":
            wait_until(
                lambda: self.exists() and self.is_visible() and self.is_enabled(),
                timeout=effective_timeout,
                interval=effective_interval,
                description=f"element '{self._meta.name}' to be enabled"
            )
        else:
            raise ValueError(f"Unknown state: {state}. Use 'exists', 'visible', or 'enabled'")
        
        return self
    
    def wait_until_visible(self, timeout: Optional[float] = None) -> Element:
        """Wait for element to become visible."""
        return self.wait("visible", timeout)
    
    def wait_until_enabled(self, timeout: Optional[float] = None) -> Element:
        """Wait for element to become enabled."""
        return self.wait("enabled", timeout)
    
    def wait_until_gone(self, timeout: Optional[float] = None) -> None:
        """Wait for element to disappear."""
        from .waits import wait_until_not
        
        config = TimeConfig.current().disappear_wait
        effective_timeout = timeout if timeout is not None else config.timeout
        
        wait_until_not(
            self.exists,
            timeout=effective_timeout,
            interval=config.interval,
            description=f"element '{self._meta.name}' to disappear"
        )
    
    # --- Actions ---
    
    def click(self) -> Element:
        """Click the element."""
        with ActionContextManager.action("click", element_name=self._meta.name):
            if hasattr(self._handle, 'click_input'):
                self._handle.click_input()
            elif hasattr(self._handle, 'click'):
                self._handle.click()
        return self
    
    def double_click(self) -> Element:
        """Double-click the element."""
        with ActionContextManager.action("double_click", element_name=self._meta.name):
            if hasattr(self._handle, 'double_click_input'):
                self._handle.double_click_input()
            elif hasattr(self._handle, 'double_click'):
                self._handle.double_click()
            else:
                self._handle.click_input()
                import time
                time.sleep(TimeConfig.current().after_double_click_pause)
                self._handle.click_input()
        return self
    
    def right_click(self) -> Element:
        """Right-click the element."""
        with ActionContextManager.action("right_click", element_name=self._meta.name):
            if hasattr(self._handle, 'right_click_input'):
                self._handle.right_click_input()
            elif hasattr(self._handle, 'click_input'):
                self._handle.click_input(button='right')
        return self
    
    def hover(self) -> Element:
        """Hover over the element."""
        with ActionContextManager.action("hover", element_name=self._meta.name):
            if hasattr(self._handle, 'move_mouse_input'):
                self._handle.move_mouse_input()
            elif hasattr(self._handle, 'set_focus'):
                self._handle.set_focus()
        return self
    
    def set_text(self, text: str, clear_first: bool = True) -> Element:
        """Type text into the element."""
        with ActionContextManager.action("set_text", element_name=self._meta.name):
            if hasattr(self._handle, 'set_edit_text'):
                self._handle.set_edit_text(text)
            elif hasattr(self._handle, 'type_keys'):
                if clear_first:
                    self._handle.type_keys('^a{DELETE}', with_spaces=True)
                self._handle.type_keys(text, with_spaces=True, with_tabs=True)
        return self
    
    def get_text(self) -> str:
        """Get the text content of the element."""
        if hasattr(self._handle, 'window_text'):
            return self._handle.window_text() or ""
        elif hasattr(self._handle, 'texts'):
            texts = self._handle.texts()
            return texts[0] if texts else ""
        elif hasattr(self._handle, 'get_value'):
            return str(self._handle.get_value() or "")
        return ""
    
    def check(self) -> Element:
        """Check a checkbox element."""
        with ActionContextManager.action("check", element_name=self._meta.name):
            if hasattr(self._handle, 'check'):
                self._handle.check()
            elif hasattr(self._handle, 'toggle'):
                state = self._handle.get_toggle_state()
                if state != 1:
                    self._handle.toggle()
            else:
                self._handle.click_input()
        return self
    
    def uncheck(self) -> Element:
        """Uncheck a checkbox element."""
        with ActionContextManager.action("uncheck", element_name=self._meta.name):
            if hasattr(self._handle, 'uncheck'):
                self._handle.uncheck()
            elif hasattr(self._handle, 'toggle'):
                state = self._handle.get_toggle_state()
                if state == 1:
                    self._handle.toggle()
            else:
                if self.get_state() == "checked":
                    self._handle.click_input()
        return self
    
    def get_state(self) -> str:
        """Get the toggle state of a checkbox."""
        try:
            if hasattr(self._handle, 'get_toggle_state'):
                state = self._handle.get_toggle_state()
                if state == 1:
                    return "checked"
                elif state == 0:
                    return "unchecked"
                else:
                    return "indeterminate"
            return "unknown"
        except Exception:
            return "unknown"
    
    def select(self, option: Any, by_index: bool = False) -> Element:
        """Select an option in a combobox."""
        with ActionContextManager.action("select", element_name=self._meta.name):
            if by_index:
                if hasattr(self._handle, 'select'):
                    self._handle.select(int(option))
            else:
                if hasattr(self._handle, 'select'):
                    self._handle.select(str(option))
        return self
    
    def select_item(
        self,
        item_text: Optional[str] = None,
        item_index: Optional[int] = None
    ) -> Element:
        """Select an item in a list."""
        with ActionContextManager.action("select_item", element_name=self._meta.name):
            if item_text is not None:
                if hasattr(self._handle, 'select'):
                    self._handle.select(item_text)
            elif item_index is not None:
                if hasattr(self._handle, 'select'):
                    self._handle.select(item_index)
        return self
    
    def item_count(self) -> int:
        """Get the number of items in a list/combobox."""
        try:
            if hasattr(self._handle, 'item_count'):
                return self._handle.item_count()
            elif hasattr(self._handle, 'items'):
                return len(self._handle.items() or [])
            return 0
        except Exception:
            return 0