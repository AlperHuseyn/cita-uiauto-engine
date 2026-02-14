# uiauto/resilient.py
"""
@file resilient.py
@brief Resilient element wrapper with automatic wait and retry mechanisms.

This module provides a wrapper around raw UI elements that automatically
handles common transient failures like staleness, visibility issues, and
timing problems.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

from .config import TimeConfig
from .context import ActionContextManager
from .element_meta import ElementMeta
from .exceptions import (ActionError, ElementNotEnabledError,
                        ElementNotFoundError, ElementNotVisibleError,
                        StaleElementError, TimeoutError, UIAutoError)
from .waits import retry, wait_until, wait_until_passes

if TYPE_CHECKING:
    from .resolver import Resolver

T = TypeVar("T")


class ResilientElement:
    """
    A wrapper around UI elements that provides automatic resilience.
    
    This class wraps a raw UI element and provides:
    - Automatic staleness detection and re-resolution
    - Built-in waits for visibility and enabled state
    - Retry mechanisms for transient failures
    - Rich error context for debugging
    
    This is the internal implementation. Users interact with Element
    which delegates to this class for enhanced operations.
    """

    def __init__(
        self,
        raw_element: Any,
        element_name: str,
        window_name: str,
        resolver: Optional[Resolver] = None,
        default_timeout: float = 10.0,
        polling_interval: float = 0.2,
        auto_wait_visible: bool = False,
        auto_wait_enabled: bool = False,
        meta: Optional[ElementMeta] = None
    ):
        """
        @param raw_element The underlying UI element object
        @param element_name Logical name of the element (from config)
        @param window_name Name of the parent window
        @param resolver Reference to resolver for re-resolution
        @param default_timeout Default timeout for waits
        @param polling_interval Polling interval for waits
        @param auto_wait_visible Whether to auto-wait for visibility before actions
        @param auto_wait_enabled Whether to auto-wait for enabled state before actions
        """
        self._raw_element = raw_element
        self._element_name = element_name
        self._window_name = window_name
        self._resolver = resolver
        self._default_timeout = default_timeout
        self._polling_interval = polling_interval
        self._auto_wait_visible = auto_wait_visible
        self._auto_wait_enabled = auto_wait_enabled
        self._resolution_time = time.time()
        self._meta = meta
    @property
    def element_name(self) -> str:
        return self._element_name
    
    @property
    def window_name(self) -> str:
        return self._window_name
    
    @property
    def handle(self) -> Any:
        """Access the underlying raw element."""
        return self._raw_element
    
    @property
    def raw(self) -> Any:
        """Alias for handle - access the underlying raw element."""
        return self._raw_element
    
    def _is_stale(self) -> bool:
        """Check if the element reference is stale."""
        try:
            if hasattr(self._raw_element, 'exists'):
                return not self._raw_element.exists()
            return False
        except Exception:
            return True
    
    def _ensure_fresh(self) -> None:
        """
        Ensure the element reference is fresh, re-resolving if stale.
        
        @throws StaleElementError if element cannot be re-resolved
        """
        if not self._is_stale():
            return
        
        if self._resolver is None:
            raise StaleElementError(
                self._element_name,
                "Element is stale and no resolver available for re-resolution"
            )
        
        config = TimeConfig.current().staleness_retry
        try:
            new_element = wait_until_passes(
                lambda: self._resolver.resolve(
                    self._element_name,
                    use_cache=False
                ),
                timeout=config.timeout,
                interval=config.interval,
                exceptions=(ElementNotFoundError, UIAutoError, Exception),
                description=f"re-resolving stale element '{self._element_name}'",
                stage="resolve"
            )
            self._raw_element = new_element.handle
            self._resolution_time = time.time()
        except TimeoutError as e:
            raise StaleElementError(
                self._element_name,
                f"Element became stale and could not be re-resolved: {e.original_exception}"
            ) from e
    
    def _ensure_visible(self, timeout: Optional[float] = None) -> None:
        """
        Ensure the element is visible before proceeding.
        
        @param timeout Override timeout (uses config default if None)
        @throws ElementNotVisibleError if element not visible within timeout
        """
        config = TimeConfig.current().visibility_wait
        effective_timeout = timeout if timeout is not None else config.timeout
        
        try:
            wait_until(
                lambda: self.is_visible(),
                timeout=effective_timeout,
                interval=config.interval,
                description=f"element '{self._element_name}' to become visible",
                stage="precondition"
            )
        except TimeoutError as e:
            raise ElementNotVisibleError(
                self._element_name,
                f"Element did not become visible within {effective_timeout}s"
            ) from e
    
    def _ensure_enabled(self, timeout: Optional[float] = None) -> None:
        """
        Ensure the element is enabled before proceeding.
        
        @param timeout Override timeout (uses config default if None)
        @throws ElementNotEnabledError if element not enabled within timeout
        """
        config = TimeConfig.current().enabled_wait
        effective_timeout = timeout if timeout is not None else config.timeout
        
        try:
            wait_until(
                lambda: self.is_enabled(),
                timeout=effective_timeout,
                interval=config.interval,
                description=f"element '{self._element_name}' to become enabled",
                stage="precondition"
            )
        except TimeoutError as e:
            raise ElementNotEnabledError(
                self._element_name,
                f"Element did not become enabled within {effective_timeout}s"
            ) from e
    
    def _prepare_for_action(self, action_name: str) -> None:
        """Prepare element for an action using centralized precondition ownership."""
        self._ensure_fresh()

        needs_visible = {"hover", "get_text", "select_item"}
        needs_enabled = {"click", "double_click", "right_click", "set_text", "check", "uncheck", "select"}

        if self._auto_wait_visible or action_name in needs_visible or action_name in needs_enabled:
            self._ensure_visible()

        if self._auto_wait_enabled or action_name in needs_enabled:
            self._ensure_enabled()
    
    def _execute_with_retry(
        self,
        action: Callable[[], T],
        action_name: str,
        retryable_exceptions: tuple = (Exception,),
    ) -> T:
        """Execute an action with automatic retry on transient failures."""
        config = TimeConfig.current().get_action_settings(action_name)
        
        with ActionContextManager.action(
            action_name,
            element_name=self._element_name,
            window_name=self._window_name
        ):
            try:
                if config.retry_count is not None:
                    return retry(
                        action,
                        max_attempts=config.retry_count,
                        interval=config.interval,
                        exceptions=retryable_exceptions,
                        description=f"{action_name} on '{self._element_name}'",
                        stage="execute"
                    )
                else:
                    return wait_until_passes(
                        action,
                        timeout=config.timeout,
                        interval=config.interval,
                        exceptions=retryable_exceptions,
                        description=f"{action_name} on '{self._element_name}'",
                        stage="execute"
                    )
            except TimeoutError as e:
                raise ActionError(
                    action=action_name,
                    element_name=self._element_name,
                    details=str(e.original_exception) if e.original_exception else str(e),
                    cause=e.original_exception
                ) from e
    
    # --- State Queries ---
    
    def exists(self) -> bool:
        """Check if the element currently exists."""
        try:
            if hasattr(self._raw_element, 'exists'):
                return bool(self._raw_element.exists())
            return True
        except Exception:
            return False
    
    def is_visible(self) -> bool:
        """Check if the element is currently visible."""
        try:
            if hasattr(self._raw_element, 'is_visible'):
                return bool(self._raw_element.is_visible())
            return True
        except Exception:
            return False
    
    def is_enabled(self) -> bool:
        """Check if the element is currently enabled."""
        try:
            if hasattr(self._raw_element, 'is_enabled'):
                return bool(self._raw_element.is_enabled())
            return True
        except Exception:
            return False
    
    # --- Wait Operations ---
    
    def wait(self, state: str = "exists", timeout: Optional[float] = None) -> ResilientElement:
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
                description=f"element '{self._element_name}' to exist",
                stage="precondition"
            )
        elif state == "visible":
            wait_until(
                lambda: self.exists() and self.is_visible(),
                timeout=effective_timeout,
                interval=effective_interval,
                description=f"element '{self._element_name}' to be visible",
                stage="precondition"
            )
        elif state == "enabled":
            wait_until(
                lambda: self.exists() and self.is_visible() and self.is_enabled(),
                timeout=effective_timeout,
                interval=effective_interval,
                description=f"element '{self._element_name}' to be enabled",
                stage="precondition"
            )
        else:
            raise ValueError(f"Unknown state: {state}. Use 'exists', 'visible', or 'enabled'")
        
        return self
    
    def wait_until_visible(self, timeout: Optional[float] = None) -> ResilientElement:
        """Wait for the element to become visible."""
        return self.wait("visible", timeout)
    
    def wait_until_enabled(self, timeout: Optional[float] = None) -> ResilientElement:
        """Wait for the element to become enabled."""
        return self.wait("enabled", timeout)
    
    def wait_until_gone(self, timeout: Optional[float] = None) -> None:
        """Wait for the element to disappear."""
        from .waits import wait_until_not
        
        config = TimeConfig.current().disappear_wait
        effective_timeout = timeout if timeout is not None else config.timeout
        
        wait_until_not(
            self.exists,
            timeout=effective_timeout,
            interval=config.interval,
            description=f"element '{self._element_name}' to disappear",
            stage="precondition"
        )
    
    # --- Actions ---
    
    def click(self) -> ResilientElement:
        """Click the element."""
        self._prepare_for_action("click")
        
        def do_click():
            if hasattr(self._raw_element, 'click_input'):
                self._raw_element.click_input()
            elif hasattr(self._raw_element, 'click'):
                self._raw_element.click()
            else:
                raise ActionError("click", self._element_name, "Click not supported")
        
        self._execute_with_retry(do_click, "click")
        return self
    
    def double_click(self) -> ResilientElement:
        """Double-click the element."""
        self._prepare_for_action("double_click")
        
        def do_double_click():
            if hasattr(self._raw_element, 'double_click_input'):
                self._raw_element.double_click_input()
            elif hasattr(self._raw_element, 'double_click'):
                self._raw_element.double_click()
            else:
                self._raw_element.click_input()
                time.sleep(TimeConfig.current().after_double_click_pause)
                self._raw_element.click_input()
        
        self._execute_with_retry(do_double_click, "double_click")
        return self
    
    def right_click(self) -> ResilientElement:
        """Right-click the element."""
        self._prepare_for_action("right_click")
        
        def do_right_click():
            if hasattr(self._raw_element, 'right_click_input'):
                self._raw_element.right_click_input()
            elif hasattr(self._raw_element, 'click_input'):
                self._raw_element.click_input(button='right')
            else:
                raise ActionError("right_click", self._element_name, "Right-click not supported")
        
        self._execute_with_retry(do_right_click, "right_click")
        return self
    
    def hover(self) -> ResilientElement:
        """Hover over the element."""
        self._prepare_for_action("hover")
        
        def do_hover():
            if hasattr(self._raw_element, 'move_mouse_input'):
                self._raw_element.move_mouse_input()
            elif hasattr(self._raw_element, 'set_focus'):
                self._raw_element.set_focus()
            else:
                raise ActionError("hover", self._element_name, "Hover not supported")
        
        self._execute_with_retry(do_hover, "hover")
        return self
    
    def set_text(self, text: str, clear_first: bool = True) -> ResilientElement:
        """Type text into the element."""
        self._prepare_for_action("set_text")
        
        def do_set_text():
            if hasattr(self._raw_element, 'set_edit_text'):
                self._raw_element.set_edit_text(text)
            elif hasattr(self._raw_element, 'type_keys'):
                if clear_first:
                    self._raw_element.type_keys('^a{DELETE}', with_spaces=True)
                self._raw_element.type_keys(text, with_spaces=True, with_tabs=True)
            else:
                raise ActionError("set_text", self._element_name, "Text input not supported")
        
        self._execute_with_retry(do_set_text, "set_text")
        return self
    
    def get_text(self) -> str:
        """Get the text content of the element."""
        self._prepare_for_action("get_text")
        
        def do_get_text() -> str:
            if hasattr(self._raw_element, 'window_text'):
                return self._raw_element.window_text() or ""
            elif hasattr(self._raw_element, 'texts'):
                texts = self._raw_element.texts()
                return texts[0] if texts else ""
            elif hasattr(self._raw_element, 'get_value'):
                return str(self._raw_element.get_value() or "")
            return ""
        
        return self._execute_with_retry(do_get_text, "get_text")
    
    def check(self) -> ResilientElement:
        """Check a checkbox."""
        self._prepare_for_action("check")
        
        def do_check():
            if hasattr(self._raw_element, 'check'):
                self._raw_element.check()
            elif hasattr(self._raw_element, 'toggle'):
                state = self._raw_element.get_toggle_state()
                if state != 1:
                    self._raw_element.toggle()
            else:
                self._raw_element.click_input()
        
        self._execute_with_retry(do_check, "check")
        return self
    
    def uncheck(self) -> ResilientElement:
        """Uncheck a checkbox."""
        self._prepare_for_action("uncheck")
        
        def do_uncheck():
            if hasattr(self._raw_element, 'uncheck'):
                self._raw_element.uncheck()
            elif hasattr(self._raw_element, 'toggle'):
                state = self._raw_element.get_toggle_state()
                if state == 1:
                    self._raw_element.toggle()
            else:
                if self.get_state() == "checked":
                    self._raw_element.click_input()
        
        self._execute_with_retry(do_uncheck, "uncheck")
        return self
    
    def get_state(self) -> str:
        """Get the toggle state of a checkbox."""
        try:
            if hasattr(self._raw_element, 'get_toggle_state'):
                state = self._raw_element.get_toggle_state()
                if state == 1:
                    return "checked"
                elif state == 0:
                    return "unchecked"
                else:
                    return "indeterminate"
            return "unknown"
        except Exception:
            return "unknown"
    
    def select(self, option: Any, by_index: bool = False) -> ResilientElement:
        """Select an option in a combobox."""
        self._prepare_for_action("select")
        
        def do_select():
            if by_index:
                if hasattr(self._raw_element, 'select'):
                    self._raw_element.select(int(option))
                else:
                    raise ActionError("select", self._element_name, "Index selection not supported")
            else:
                if hasattr(self._raw_element, 'select'):
                    self._raw_element.select(str(option))
                else:
                    raise ActionError("select", self._element_name, "Text selection not supported")
        
        self._execute_with_retry(do_select, "select")
        return self
    
    def select_item(
        self,
        item_text: Optional[str] = None,
        item_index: Optional[int] = None
    ) -> ResilientElement:
        """Select an item in a list."""
        self._prepare_for_action("select_item")
        
        def do_select_item():
            if item_text is not None:
                if hasattr(self._raw_element, 'select'):
                    self._raw_element.select(item_text)
                else:
                    raise ActionError("select_item", self._element_name, "Item selection not supported")
            elif item_index is not None:
                if hasattr(self._raw_element, 'select'):
                    self._raw_element.select(item_index)
                else:
                    raise ActionError("select_item", self._element_name, "Index selection not supported")
            else:
                raise ActionError("select_item", self._element_name, "Either item_text or item_index required")
        
        self._execute_with_retry(do_select_item, "select_item")
        return self
    
    def item_count(self) -> int:
        """Get the number of items in a list/combobox."""
        try:
            if hasattr(self._raw_element, 'item_count'):
                return self._raw_element.item_count()
            elif hasattr(self._raw_element, 'items'):
                return len(self._raw_element.items() or [])
            return 0
        except Exception:
            return 0