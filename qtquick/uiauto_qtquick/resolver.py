# uiauto_qtquick/resolver.py
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from uiauto_core.interfaces import IResolver, IElement
from uiauto_core.repository import Repository
from uiauto_core.exceptions import LocatorAttempt, WindowNotFoundError, ElementNotFoundError
from uiauto_core.waits import wait_until

from .session import QtQuickSession
from .element import QtQuickElement, ElementMeta
from .artifacts import make_artifacts


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
    # Only pass pywinauto-recognized kwargs to child_window/window search
    # Note: name/name_re are NOT pywinauto native, so we'll handle them separately
    allowed = {"auto_id", "title", "title_re", "control_type", "class_name", "best_match", "found_index", "process", "handle"}
    return {k: v for k, v in locator.items() if k in allowed}


class QtQuickResolver(IResolver):
    """
    Resolves windows and elements by semantic names using repository specs.
    Implements multi-strategy locator attempts with retries and filters.
    QtQuick-specific implementation with support for element_info.name matching.
    """

    def __init__(self, session: QtQuickSession, repo: Repository):
        self.session = session
        self.repo = repo

    @property
    def timeout(self) -> float:
        return self.repo.app.default_timeout

    @property
    def interval(self) -> float:
        return self.repo.app.polling_interval

    def resolve_window(self, window_name: str):
        wspec = self.repo.get_window_spec(window_name)
        locators = wspec.get("locators", [])
        attempts: List[LocatorAttempt] = []
        last_error: Optional[str] = None

        def try_one(locator: Dict[str, Any]):
            safe = _sanitize_locator(locator)
            # Prefer app_window when possible; fallback to desktop
            try:
                if self.session.app:
                    w = self.session.app_window(**safe)
                else:
                    w = self.session.desktop_window(**safe)
            except Exception:
                w = self.session.desktop_window(**safe)

            # Wait until exists/visible
            def pred():
                try:
                    return w.exists() and w.is_visible()
                except Exception:
                    return False

            wait_until(pred, timeout=self.timeout, interval=self.interval, description=f"window '{window_name}' exists+visible")
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
            # If there's a title_re in any locator, attempt it for artifacts
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

        raise WindowNotFoundError(window_name, attempts=attempts, timeout=self.timeout, last_error=last_error, artifacts=artifacts)

    def resolve(self, element_name: str, overrides: Optional[Dict[str, Any]] = None) -> IElement:
        overrides = overrides or {}
        espec = self.repo.get_element_spec(element_name)
        window_name = espec["window"]
        window = self.resolve_window(window_name)

        locators = list(espec.get("locators", []))
        # Apply overrides by prepending a locator attempt (highest priority)
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
                wrapped = QtQuickElement(elem, meta=meta, default_timeout=self.timeout, polling_interval=self.interval)
                
                # For name/name_re based locators, skip the exists() wait since descendants() already verified presence
                # QtQuick controls found via element_info.name matching may not respond correctly to exists() checks
                if not is_name_based:
                    wrapped.wait("exists", timeout=self.timeout)
                
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
            timeout=self.timeout,
            last_error=last_error,
            artifacts=artifacts,
        )

    def _resolve_in_window(self, window, locator: Dict[str, Any]):
        """
        Resolution strategy:
        1) If name/name_re provided, use descendants matching on element_info.name
        2) Try child_window(**locator) directly (fast, scoped) for other locators
        3) If title/title_re provided and child_window fails, search descendants by control_type and filter
        4) Apply found_index only if provided
        """
        control_type = locator.get("control_type")
        name = locator.get("name")
        name_re = locator.get("name_re")
        title = locator.get("title")
        title_re = locator.get("title_re")
        found_index = locator.get("found_index")
        
        # Strategy 1: If name/name_re is provided, use descendants-based matching on element_info.name
        if name is not None or name_re is not None:
            try:
                if control_type:
                    items = window.descendants(control_type=control_type)
                else:
                    items = window.descendants()

                filtered = []
                for it in items:
                    # Match on element_info.name
                    try:
                        elem_name = it.element_info.name
                    except Exception:
                        elem_name = ""
                    
                    if not _matches_name(elem_name, name=name, name_re=name_re):
                        continue

                    # Optional: ignore titlebar buttons
                    if self.repo.app.ignore_titlebar_buttons:
                        try:
                            t = it.window_text()
                            if it.friendly_class_name() == "Button" and t in TITLEBAR_BUTTON_TITLES:
                                continue
                        except Exception:
                            pass

                    # QtQuick controls found via descendants are already present
                    filtered.append(it)

                if not filtered:
                    raise RuntimeError("No matching descendants by name found")

                # Sort by visibility preference (visible first)
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

                # default: first match (most visible)
                return filtered[0]
            except Exception:
                raise
        
        # Strategy 2: Try child_window for other locators
        safe = _sanitize_locator(locator)
        try:
            cw = window.child_window(**safe)
            # exists() can raise sometimes; wrap
            def pred():
                try:
                    return cw.exists()
                except Exception:
                    return False
            wait_until(pred, timeout=min(1.5, self.timeout), interval=self.interval, description="child_window exists quick")
            return cw
        except Exception:
            pass

        # Strategy 3: descendants-based filtering for title/title_re (more expensive)
        try:
            if control_type:
                items = window.descendants(control_type=control_type)
            else:
                items = window.descendants()

            # Filter by title / regex if present
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

                # Optional: ignore titlebar buttons
                if self.repo.app.ignore_titlebar_buttons:
                    try:
                        if it.friendly_class_name() == "Button" and t in TITLEBAR_BUTTON_TITLES:
                            continue
                    except Exception:
                        pass

                # Prefer visible elements
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

            # default: first match
            return filtered[0]
        except Exception:
            raise
