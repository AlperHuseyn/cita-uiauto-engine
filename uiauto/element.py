# uiauto/element.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .waits import wait_until


@dataclass
class ElementMeta:
    name: str
    window_name: str
    used_locator: Dict[str, Any]
    found_via_name: bool = False  # Track if element was found via name/name_re matching


class Element:
    """
    Thin wrapper around a pywinauto element handle.
    """
    def __init__(self, handle, meta: ElementMeta, default_timeout: float, polling_interval: float):
        self.handle = handle
        self.meta = meta
        self.default_timeout = default_timeout
        self.polling_interval = polling_interval

    def exists(self) -> bool:
        # For elements found via name/name_re matching (QtQuick), 
        # handle.exists() doesn't work reliably because it tries to re-find 
        # the element using standard pywinauto mechanisms.
        # Since we already verified presence via descendants(), we return True.
        # Note: This assumes the element remains valid for the lifetime of this wrapper.
        # If the UI changes significantly, create a new element wrapper.
        if self.meta.found_via_name:
            return True
        try:
            return bool(self.handle.exists())
        except Exception:
            return False

    def is_visible(self) -> bool:
        try:
            return bool(self.handle.is_visible())
        except Exception:
            return False

    def is_enabled(self) -> bool:
        try:
            return bool(self.handle.is_enabled())
        except Exception:
            return False

    def wait(self, state: str = "exists", timeout: Optional[float] = None) -> "Element":
        timeout = self.default_timeout if timeout is None else float(timeout)

        def pred():
            if state == "exists":
                return self.exists()
            if state == "visible":
                return self.exists() and self.is_visible()
            if state == "enabled":
                return self.exists() and self.is_visible() and self.is_enabled()
            raise ValueError(f"Unknown wait state: {state}")

        wait_until(pred, timeout=timeout, interval=self.polling_interval, description=f"{self.meta.name} to be {state}")
        return self

    def click(self) -> None:
        # click_input is more reliable for UI
        self.handle.click_input()

    def set_text(self, text: str) -> None:
        # For Edit controls on UIA, set_edit_text is usually best
        try:
            self.handle.set_edit_text(text)
        except Exception:
            # fallback
            self.handle.set_text(text)

    def type_keys(self, text: str, with_spaces: bool = True, set_foreground: bool = True) -> None:
        self.handle.type_keys(text, with_spaces=with_spaces, set_foreground=set_foreground)

    def window_text(self) -> str:
        try:
            return self.handle.window_text()
        except Exception:
            return ""

    def rectangle(self):
        return self.handle.rectangle()
