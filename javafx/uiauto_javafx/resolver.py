# javafx/uiauto_javafx/resolver.py
"""JavaFX element resolver using Java Access Bridge."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from uiauto_core import Repository, wait_until, WindowNotFoundError, ElementNotFoundError, LocatorAttempt

from .session import JavaFXSession
from .element import JavaFXElement, ElementMeta


class JavaFXResolver:
    """
    Resolves windows and elements by semantic names using repository specs.
    JavaFX implementation using Java Access Bridge.
    """
    
    def __init__(self, session: JavaFXSession, repo: Repository):
        """
        Initialize resolver.
        
        Args:
            session: JavaFX session instance
            repo: Repository with object map
        """
        self.session = session
        self.repo = repo
    
    @property
    def timeout(self) -> float:
        return self.repo.app.default_timeout
    
    @property
    def interval(self) -> float:
        return self.repo.app.polling_interval
    
    def resolve_window(self, window_name: str) -> Any:
        """
        Resolve window by semantic name.
        
        Args:
            window_name: Window name from object map
            
        Returns:
            Window object (java.awt.Window)
        """
        wspec = self.repo.get_window_spec(window_name)
        locators = wspec.get("locators", [])
        attempts: List[LocatorAttempt] = []
        last_error: Optional[str] = None
        
        def try_one(locator: Dict[str, Any]):
            title = locator.get('title')
            title_re = locator.get('title_re')
            
            kwargs = {}
            if title:
                kwargs['title'] = title
            elif title_re:
                kwargs['title_re'] = title_re
            
            # Try to get window
            w = self.session.desktop_window(**kwargs)
            
            # Wait until window is visible
            def pred():
                try:
                    return w.isVisible()
                except Exception:
                    return False
            
            wait_until(pred, timeout=self.timeout, interval=self.interval,
                      description=f"window '{window_name}' visible")
            return w
        
        for locator in locators:
            try:
                w = try_one(locator)
                return w
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                attempts.append(LocatorAttempt(kind="window", locator=locator, error=last_error))
        
        raise WindowNotFoundError(
            window_name,
            attempts=attempts,
            timeout=self.timeout,
            last_error=last_error,
            artifacts={},  # Could add JAB-based artifacts later
        )
    
    def resolve(self, element_name: str, overrides: Optional[Dict[str, Any]] = None) -> JavaFXElement:
        """
        Resolve element by semantic name.
        
        Args:
            element_name: Element name from object map
            overrides: Optional locator overrides
            
        Returns:
            JavaFXElement instance
        """
        overrides = overrides or {}
        espec = self.repo.get_element_spec(element_name)
        window_name = espec["window"]
        window = self.resolve_window(window_name)
        
        # Get accessible context for window
        window_context = self.session.bridge.get_accessible_context(window)
        if not window_context:
            raise RuntimeError(f"Could not get AccessibleContext for window: {window_name}")
        
        locators = list(espec.get("locators", []))
        # Apply overrides by prepending
        if overrides:
            locators = [overrides] + locators
        
        attempts: List[LocatorAttempt] = []
        last_error: Optional[str] = None
        
        for locator in locators:
            try:
                context = self._resolve_in_window(window_context, locator)
                is_name_based = "name" in locator or "name_re" in locator
                
                meta = ElementMeta(
                    name=element_name,
                    window_name=window_name,
                    used_locator=locator,
                    found_via_name=is_name_based,
                )
                
                wrapped = JavaFXElement(
                    context,
                    meta=meta,
                    default_timeout=self.timeout,
                    polling_interval=self.interval,
                )
                
                # For name-based, we already verified it exists
                if not is_name_based:
                    wrapped.wait("exists", timeout=self.timeout)
                
                return wrapped
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                attempts.append(LocatorAttempt(kind="element", locator=locator, error=last_error))
        
        raise ElementNotFoundError(
            element_name=element_name,
            window_name=window_name,
            attempts=attempts,
            timeout=self.timeout,
            last_error=last_error,
            artifacts={},
        )
    
    def _resolve_in_window(self, window_context: Any, locator: Dict[str, Any]) -> Any:
        """
        Resolve element within a window using locator.
        
        Args:
            window_context: Window's AccessibleContext
            locator: Locator dict
            
        Returns:
            AccessibleContext of element
        """
        name = locator.get("name")
        name_re = locator.get("name_re")
        control_type = locator.get("control_type")
        found_index = locator.get("found_index")
        
        # Strategy 1: Find by name (exact or regex)
        if name:
            context = self.session.bridge.find_element_by_name(window_context, name)
            if context:
                return context
            raise RuntimeError(f"Element not found by name: {name}")
        
        if name_re:
            pattern = re.compile(name_re)
            # Search through tree
            result = [None]
            
            def matcher(ctx):
                try:
                    ctx_name = ctx.getAccessibleName()
                    if ctx_name and pattern.search(str(ctx_name)):
                        result[0] = ctx
                        return True
                except Exception:
                    pass
                return False
            
            self.session.bridge._traverse_tree(window_context, matcher, max_depth=10)
            if result[0]:
                return result[0]
            raise RuntimeError(f"Element not found by name_re: {name_re}")
        
        # Strategy 2: Find by role (control_type)
        if control_type:
            role = self.session.bridge.map_control_type_to_role(control_type)
            elements = self.session.bridge.find_elements_by_role(window_context, role, max_depth=10)
            
            if not elements:
                raise RuntimeError(f"No elements found with role: {role}")
            
            # Filter by visibility
            visible_elements = []
            for elem in elements:
                try:
                    state_set = elem.getAccessibleStateSet()
                    if state_set:
                        from javax.accessibility import AccessibleState
                        if state_set.contains(AccessibleState.VISIBLE):
                            visible_elements.append(elem)
                except Exception:
                    pass
            
            if not visible_elements:
                visible_elements = elements  # Fall back to all if none visible
            
            # Apply found_index
            if found_index is not None:
                idx = int(found_index)
                if idx < 0 or idx >= len(visible_elements):
                    raise IndexError(f"found_index {idx} out of range for {len(visible_elements)} matches")
                return visible_elements[idx]
            
            # Return first match
            return visible_elements[0]
        
        raise RuntimeError("No valid locator strategy found")
