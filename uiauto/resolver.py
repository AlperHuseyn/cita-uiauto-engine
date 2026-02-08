# uiauto/resolver.py
"""
@file resolver.py
@brief Resolves windows and elements by semantic names using repository specs.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from .repository import Repository
from .session import Session
from .element import Element, ElementMeta
from .exceptions import LocatorAttempt, WindowNotFoundError, ElementNotFoundError
from .waits import wait_until
from .artifacts import make_artifacts
from .context import ActionContextManager
from .config import TimeConfig


TITLEBAR_BUTTON_TITLES = {"Close", "Minimize", "Maximize"}


def _matches_title(text: str, title: Optional[str], title_re: Optional[str]) -> bool:
    if title is not None and text != title:
        return False
    if title_re is not None:
        if not re.search(title_re, text or ""):
            return False
    return True


def _matches_name(element_name: str, name: Optional[str], name_re: Optional[str]) -> bool:
    """Check if element_info.name matches the provided name or name_re pattern."""
    if name is not None and element_name != name:
        return False
    if name_re is not None:
        if not re.search(name_re, element_name or ""):
            return False
    return True


def _is_name_based_locator(locator: Dict[str, Any]) -> bool:
    """Check if locator uses name or name_re for matching."""
    return "name" in locator or "name_re" in locator


def _sanitize_locator(locator: Dict[str, Any]) -> Dict[str, Any]:
    """Only pass pywinauto-recognized kwargs to child_window/window search."""
    allowed = {"auto_id", "title", "title_re", "control_type", "class_name", "best_match", "found_index", "process", "handle"}
    return {k: v for k, v in locator.items() if k in allowed}


class Resolver:
    """
    Resolves windows and elements by semantic names using repository specs.
    Implements multi-strategy locator attempts with retries and filters.
    """

    def __init__(self, session: Session, repo: Repository):
        """
        @param session Session instance for UI automation backend
        @param repo Repository with element/window specifications
        """
        self.session = session
        self.repo = repo
        self._element_cache: Dict[str, Element] = {}
        self._cache_enabled: bool = True

    @property
    def timeout(self) -> float:
        """Default timeout from repository configuration."""
        return TimeConfig.current().resolve_element.timeout

    @property
    def interval(self) -> float:
        """Polling interval from repository configuration."""
        return TimeConfig.current().resolve_element.interval
    
    def enable_cache(self, enabled: bool = True) -> None:
        """Enable or disable element caching."""
        self._cache_enabled = enabled
        if not enabled:
            self._element_cache.clear()
    
    def clear_cache(self) -> None:
        """Clear the element cache."""
        self._element_cache.clear()

    def resolve_window(self, window_name: str, timeout: Optional[float] = None) -> Any:
        """
        Resolve a window by name.
        
        @param window_name Logical window name from configuration
        @param timeout Override timeout (uses default if None)
        @return Window wrapper object
        @throws WindowNotFoundError if window not found within timeout
        """
        config = TimeConfig.current().resolve_window
        effective_timeout = timeout if timeout is not None else config.timeout
        effective_interval = config.interval
        wspec = self.repo.get_window_spec(window_name)
        locators = wspec.get("locators", [])
        attempts: List[LocatorAttempt] = []
        last_error: Optional[str] = None

        def try_one(locator: Dict[str, Any]):
            safe = _sanitize_locator(locator)
            try:
                if self.session.app:
                    w = self.session.app_window(**safe)
                else:
                    w = self.session.desktop_window(**safe)
            except Exception:
                w = self.session.desktop_window(**safe)

            def pred():
                try:
                    return w.exists() and w.is_visible()
                except Exception:
                    return False

            wait_until(
                pred,
                timeout=effective_timeout,
                interval=effective_interval,
                description=f"window '{window_name}' exists+visible"
            )
            return w

        for locator in locators:
            try:
                w = try_one(locator)
                return w
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                attempts.append(LocatorAttempt(kind="window", locator=locator, error=last_error))

        # Artifacts: try best guess window from Desktop by broad regex if provided
        artifacts = {}
        try:
            title_re = None
            for loc in locators:
                if "title_re" in loc:
                    title_re = loc["title_re"]
                    break
            if title_re:
                w = self.session.desktop_window(title_re=title_re)
                artifacts = make_artifacts(w, self.repo.app.artifacts_dir, f"window_{window_name}")
        except Exception:
            pass

        raise WindowNotFoundError(
            window_name,
            attempts=attempts,
            timeout=effective_timeout,
            last_error=last_error,
            artifacts=artifacts
        )

    def resolve(
        self,
        element_name: str,
        overrides: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        use_cache: bool = True,
    ) -> Element:
        """
        Resolve an element by name.
        
        @param element_name Logical element name from configuration
        @param overrides Optional locator overrides (highest priority)
        @param timeout Override timeout (uses default if None)
        @param use_cache Whether to use cached element if available
        @return Element wrapper object
        @throws ElementNotFoundError if element not found within timeout
        """
        effective_timeout = timeout if timeout is not None else self.timeout
        overrides = overrides or {}
        config = TimeConfig.current().resolve_element
        if timeout is None:
            effective_timeout = config.timeout
        effective_interval = config.interval
        
        espec = self.repo.get_element_spec(element_name)
        window_name = espec["window"]
        
        # Check cache first
        cache_key = f"{window_name}::{element_name}"
        if use_cache and self._cache_enabled and cache_key in self._element_cache:
            cached = self._element_cache[cache_key]
            try:
                if cached.exists():
                    return cached
            except Exception:
                pass
            del self._element_cache[cache_key]
        
        with ActionContextManager.action("resolve", element_name=element_name, window_name=window_name):
            window = self.resolve_window(window_name)

            locators = list(espec.get("locators", []))
            if overrides:
                locators = [overrides] + locators

            attempts: List[LocatorAttempt] = []
            last_error: Optional[str] = None

            for locator in locators:
                try:
                    elem = self._resolve_in_window(window, locator)
                    is_name_based = _is_name_based_locator(locator)
                    meta = ElementMeta(
                        name=element_name, 
                        window_name=window_name, 
                        used_locator=locator,
                        found_via_name=is_name_based
                    )
                    
                    wrapped = Element(
                        elem,
                        meta=meta,
                        default_timeout=effective_timeout,
                        polling_interval=effective_interval,
                    )
                    
                    # For name/name_re based locators, skip exists() wait
                    if not is_name_based:
                        wrapped.wait("exists", timeout=effective_timeout)
                    
                    # Cache the result
                    if self._cache_enabled:
                        self._element_cache[cache_key] = wrapped
                    
                    return wrapped
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}"
                    attempts.append(LocatorAttempt(kind="element", locator=locator, error=last_error))

            artifacts = {}
            try:
                artifacts = make_artifacts(window, self.repo.app.artifacts_dir, f"element_{element_name}")
            except Exception:
                pass

            raise ElementNotFoundError(
                element_name=element_name,
                window_name=window_name,
                attempts=attempts,
                timeout=effective_timeout,
                last_error=last_error,
                artifacts=artifacts,
            )
    
    def exists(
        self,
        element_name: str,
        timeout: float = 0,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if an element exists (optionally with waiting).
        
        @param element_name Logical name of the element
        @param timeout How long to wait (0 = immediate check)
        @param overrides Optional locator overrides
        @return True if element exists, False otherwise
        """
        try:
            elem = self.resolve(element_name, overrides=overrides, timeout=max(timeout, 0.5), use_cache=False)
            return elem.exists()
        except (ElementNotFoundError, WindowNotFoundError):
            return False
    
    def wait_for_element(
        self,
        element_name: str,
        timeout: Optional[float] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Element:
        """
        Explicitly wait for an element to appear.
        
        @param element_name Logical name of the element
        @param timeout Override timeout
        @param overrides Optional locator overrides
        @return Element when found
        """
        return self.resolve(element_name, overrides=overrides, timeout=timeout)
    
    def wait_for_element_gone(
        self,
        element_name: str,
        timeout: Optional[float] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Wait for an element to disappear.
        
        @param element_name Logical name of the element
        @param timeout Override timeout
        @param overrides Optional locator overrides
        @throws TimeoutError if element doesn't disappear
        """
        from .waits import wait_until_not
        
        config = TimeConfig.current().disappear_wait
        effective_timeout = timeout if timeout is not None else config.timeout
        effective_interval = config.interval
        
        wait_until_not(
            lambda: self.exists(element_name, timeout=0, overrides=overrides),
            timeout=effective_timeout,
            interval=effective_interval,
            description=f"element '{element_name}' to disappear"
        )

    def _resolve_in_window(self, window: Any, locator: Dict[str, Any]) -> Any:
        """
        Resolution strategy:
        1) If name/name_re provided, use descendants matching on element_info.name
        2) Try child_window(**locator) directly (fast, scoped) for other locators
        3) If title/title_re provided and child_window fails, search descendants
        4) Apply found_index only if provided
        """
        control_type = locator.get("control_type")
        name = locator.get("name")
        name_re = locator.get("name_re")
        title = locator.get("title")
        title_re = locator.get("title_re")
        found_index = locator.get("found_index")
        
        # Strategy 1: If name/name_re is provided, use descendants-based matching
        if name is not None or name_re is not None:
            try:
                if control_type:
                    items = window.descendants(control_type=control_type)
                else:
                    items = window.descendants()

                filtered = []
                for it in items:
                    try:
                        elem_name = it.element_info.name
                    except Exception:
                        elem_name = ""
                    
                    if not _matches_name(elem_name, name=name, name_re=name_re):
                        continue

                    if self.repo.app.ignore_titlebar_buttons:
                        try:
                            t = it.window_text()
                            if it.friendly_class_name() == "Button" and t in TITLEBAR_BUTTON_TITLES:
                                continue
                        except Exception:
                            pass

                    filtered.append(it)

                if not filtered:
                    raise RuntimeError("No matching descendants by name found")

                def vis_key(x):
                    try:
                        return 1 if x.is_visible() else 0
                    except Exception:
                        return 0
                filtered.sort(key=vis_key, reverse=True)

                if found_index is not None:
                    idx = int(found_index)
                    if idx < 0 or idx >= len(filtered):
                        raise IndexError(f"found_index {idx} out of range for {len(filtered)} matches")
                    return filtered[idx]

                return filtered[0]
            except Exception:
                raise
        
        # Strategy 2: Try child_window for other locators
        safe = _sanitize_locator(locator)
        try:
            cw = window.child_window(**safe)
            def pred():
                try:
                    return cw.exists()
                except Exception:
                    return False
            config = TimeConfig.current().child_window_quick
            wait_until(
                pred,
                timeout=config.timeout,
                interval=config.interval,
                description="child_window exists quick",
            )
            return cw
        except Exception:
            pass

        # Strategy 3: descendants-based filtering for title/title_re
        try:
            if control_type:
                items = window.descendants(control_type=control_type)
            else:
                items = window.descendants()

            filtered = []
            for it in items:
                try:
                    t = it.window_text()
                except Exception:
                    t = ""
                if title is None and title_re is None:
                    ok = True
                else:
                    ok = _matches_title(t, title=title, title_re=title_re)

                if not ok:
                    continue

                if self.repo.app.ignore_titlebar_buttons:
                    try:
                        if it.friendly_class_name() == "Button" and t in TITLEBAR_BUTTON_TITLES:
                            continue
                    except Exception:
                        pass

                try:
                    if hasattr(it, "is_visible") and not it.is_visible():
                        continue
                except Exception:
                    pass

                filtered.append(it)

            if not filtered:
                raise RuntimeError("No matching descendants found")

            if found_index is not None:
                idx = int(found_index)
                if idx < 0 or idx >= len(filtered):
                    raise IndexError(f"found_index {idx} out of range for {len(filtered)} matches")
                return filtered[idx]

            return filtered[0]
        except Exception:
            raise