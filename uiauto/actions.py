# uiauto/actions.py
from __future__ import annotations

from typing import Any, Dict, Optional

from pywinauto.keyboard import send_keys

from .exceptions import ActionError
from .resolver import Resolver


class Actions:
    """
    Keyword-like action library operating on Resolver + Element wrappers.
    """

    def __init__(self, resolver: Resolver):
        self.resolver = resolver

    def click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            el.click()
        except Exception as e:
            raise ActionError("click", element_name=element, cause=e)

    def type(self, element: str, text: str, overrides: Optional[Dict[str, Any]] = None, clear: bool = True) -> None:
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait("enabled")
            if clear:
                try:
                    el.set_text("")  # clear
                except Exception:
                    pass
            el.set_text(text)
        except Exception as e:
            raise ActionError("type", element_name=element, cause=e)

    def wait_for(self, element: str, state: str = "visible", timeout: Optional[float] = None, overrides: Optional[Dict[str, Any]] = None) -> None:
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            el.wait(state, timeout=timeout)
        except Exception as e:
            raise ActionError("wait_for", element_name=element, cause=e)

    def assert_state(self, element: str, state: str = "visible", overrides: Optional[Dict[str, Any]] = None) -> None:
        try:
            el = self.resolver.resolve(element, overrides=overrides)
            if state == "exists" and not el.exists():
                raise AssertionError("Expected exists, but not found")
            if state == "visible" and not (el.exists() and el.is_visible()):
                raise AssertionError("Expected visible, but not visible")
            if state == "enabled" and not (el.exists() and el.is_visible() and el.is_enabled()):
                raise AssertionError("Expected enabled, but not enabled")
        except Exception as e:
            raise ActionError("assert_state", element_name=element, cause=e)

    def close_window(self, window_name: str) -> None:
        try:
            w = self.resolver.resolve_window(window_name)
            w.close()
        except Exception as e:
            raise ActionError("close_window", element_name=window_name, cause=e)

    def hotkey(self, keys: str) -> None:
        """
        Global veya aktif pencereye klavye kombinasyonu gönderir.
        Örnek: '^l' = Ctrl+L
        """
        try:
            send_keys(keys, pause=0.05)
        except Exception as e:
            raise ActionError("hotkey", details=f"keys={keys}", cause=e)

