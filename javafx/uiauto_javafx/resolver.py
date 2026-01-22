# javafx/uiauto_javafx/resolver.py
"""JavaFX resolver implementation using Java Access Bridge."""
from __future__ import annotations
import re
import logging
from typing import Any, Dict, List, Optional

from uiauto_core.repository import Repository
from uiauto_core.interfaces import IResolver
from uiauto_core.exceptions import LocatorAttempt, WindowNotFoundError, ElementNotFoundError
from uiauto_core.waits import wait_until

from .session import JavaFXSession
from .element import JavaFXElement, JavaFXElementMeta


# Map UIA control types to Java Accessibility roles
CONTROL_TYPE_TO_ROLE_MAP = {
    "Button": "PUSH_BUTTON",
    "Edit": "TEXT",
    "Text": "TEXT",
    "ComboBox": "COMBO_BOX",
    "List": "LIST",
    "ListItem": "LIST_ITEM",
    "CheckBox": "CHECK_BOX",
    "RadioButton": "RADIO_BUTTON",
    "TabControl": "PAGE_TAB_LIST",
    "Tab": "PAGE_TAB",
    "Tree": "TREE",
    "TreeItem": "TREE_ITEM",
    "Table": "TABLE",
    "MenuItem": "MENU_ITEM",
    "Menu": "MENU",
    "ToolBar": "TOOL_BAR",
    "StatusBar": "STATUS_BAR",
    "Window": "FRAME",
    "Pane": "PANEL",
    "Group": "PANEL",
}


class JavaFXResolver(IResolver):
    """
    JavaFX resolver using Java Access Bridge.
    
    Resolves windows and elements by semantic names using JAB APIs.
    """
    
    def __init__(self, session: JavaFXSession, repo: Repository):
        """
        Initialize resolver.
        
        @param session JavaFX session instance
        @param repo Repository with object map
        """
        self.session = session
        self.repo = repo
        self.log = logging.getLogger("uiauto.javafx")
    
    @property
    def timeout(self) -> float:
        """Get default timeout from repository."""
        return self.repo.app.default_timeout
    
    @property
    def interval(self) -> float:
        """Get polling interval from repository."""
        return self.repo.app.polling_interval
    
    def resolve_window(self, window_name: str) -> Any:
        """
        Resolve window by semantic name.
        
        @param window_name Window name from object map
        @return Window AccessibleContext
        """
        wspec = self.repo.get_window_spec(window_name)
        locators = wspec.get("locators", [])
        attempts: List[LocatorAttempt] = []
        last_error: Optional[str] = None
        
        def try_one(locator: Dict[str, Any]):
            """Try to find window with one locator."""
            title = locator.get("title")
            title_re = locator.get("title_re")
            
            if title:
                window = self.session.bridge.find_window_by_title(title, exact=True)
            elif title_re:
                window = self.session.bridge.find_window_by_title(title_re, exact=False)
            else:
                # Fallback to app_window
                window = self.session.app_window()
            
            if window is None:
                raise RuntimeError("Window not found")
            
            return window
        
        for locator in locators:
            try:
                w = try_one(locator)
                return w
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                attempts.append(LocatorAttempt(kind="window", locator=locator, error=last_error))
        
        # If all attempts failed
        raise WindowNotFoundError(
            window_name,
            attempts=attempts,
            timeout=self.timeout,
            last_error=last_error,
        )
    
    def resolve(self, element_name: str, overrides: Optional[Dict[str, Any]] = None) -> JavaFXElement:
        """
        Resolve element by semantic name.
        
        @param element_name Element name from object map
        @param overrides Optional locator overrides
        @return JavaFX element wrapper
        """
        overrides = overrides or {}
        espec = self.repo.get_element_spec(element_name)
        window_name = espec["window"]
        window = self.resolve_window(window_name)
        
        locators = list(espec.get("locators", []))
        # Apply overrides by prepending
        if overrides:
            locators = [overrides] + locators
        
        attempts: List[LocatorAttempt] = []
        last_error: Optional[str] = None
        
        for locator in locators:
            try:
                ctx = self._resolve_in_window(window, locator)
                meta = JavaFXElementMeta(
                    name=element_name,
                    window_name=window_name,
                    used_locator=locator,
                )
                wrapped = JavaFXElement(ctx, meta=meta, default_timeout=self.timeout, polling_interval=self.interval)
                
                # Verify exists
                wrapped.wait("exists", timeout=self.timeout)
                return wrapped
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                attempts.append(LocatorAttempt(kind="element", locator=locator, error=last_error))
        
        # All attempts failed
        raise ElementNotFoundError(
            element_name=element_name,
            window_name=window_name,
            attempts=attempts,
            timeout=self.timeout,
            last_error=last_error,
        )
    
    def _resolve_in_window(self, window: Any, locator: Dict[str, Any]) -> Any:
        """
        Resolve element within window using locator.
        
        @param window Window AccessibleContext
        @param locator Locator dict from object map
        @return Element AccessibleContext
        """
        name = locator.get("name")
        control_type = locator.get("control_type")
        found_index = locator.get("found_index")
        
        # Strategy 1: If name is provided, search by name
        if name:
            role = self._map_control_type_to_role(control_type) if control_type else None
            
            if role:
                # Search by name AND role
                elem = self.session.bridge.find_element_by_name_and_role(
                    window, name, role, max_depth=15
                )
            else:
                # Search by name only
                elem = self.session.bridge.find_element_by_name(
                    window, name, max_depth=15
                )
            
            if elem:
                return elem
            else:
                raise RuntimeError(f"Element not found by name: {name}")
        
        # Strategy 2: Search by role/control_type
        if control_type:
            role = self._map_control_type_to_role(control_type)
            elements = self.session.bridge.find_elements_by_role(
                window, role, max_depth=15
            )
            
            if not elements:
                raise RuntimeError(f"No elements found with role: {role}")
            
            if found_index is not None:
                idx = int(found_index)
                if idx < 0 or idx >= len(elements):
                    raise IndexError(f"found_index {idx} out of range (found {len(elements)} elements)")
                return elements[idx]
            
            # Default: first match
            return elements[0]
        
        # Strategy 3: Try title/title_re for backward compatibility
        title = locator.get("title")
        if title:
            # Search for element with matching accessible name
            elem = self.session.bridge.find_element_by_name(
                window, title, max_depth=15
            )
            if elem:
                return elem
        
        raise RuntimeError(f"Could not resolve element with locator: {locator}")
    
    def _map_control_type_to_role(self, control_type: str) -> str:
        """
        Map UIA control type to Java Accessibility role.
        
        @param control_type Control type from locator
        @return Java Accessibility role string
        """
        return CONTROL_TYPE_TO_ROLE_MAP.get(control_type, control_type.upper())
