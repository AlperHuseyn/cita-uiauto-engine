# core/uiauto_core/repository.py
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml

from uiauto_core.exceptions import ConfigError


ALLOWED_LOCATOR_KEYS = {
    "auto_id",
    "name",
    "name_re",
    "title",
    "title_re",
    "control_type",
    "class_name",
    "found_index",
    "best_match",
    "backend",
    "process",
    "handle",
}


@dataclass(frozen=True)
class AppConfig:
    backend: str = "uia"
    default_timeout: float = 10.0
    polling_interval: float = 0.2
    artifacts_dir: str = "artifacts"
    strict_locator_keys: bool = True
    ignore_titlebar_buttons: bool = True


class Repository:
    """
    Loads elements.yaml (object map). Provides access to app config, windows, elements.
    """

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self._raw: Dict[str, Any] = self._load_yaml(self.path)
        self._app = self._parse_app_config(self._raw.get("app", {}))
        self._windows = self._raw.get("windows", {}) or {}
        self._elements = self._raw.get("elements", {}) or {}

        self._validate()

    @staticmethod
    def _load_yaml(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise ConfigError(f"Object map YAML not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ConfigError("Object map YAML must be a mapping at root.")
            return data
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML: {e}") from e

    @staticmethod
    def _parse_app_config(d: Dict[str, Any]) -> AppConfig:
        return AppConfig(
            backend=str(d.get("backend", "uia")),
            default_timeout=float(d.get("default_timeout", 10.0)),
            polling_interval=float(d.get("polling_interval", 0.2)),
            artifacts_dir=str(d.get("artifacts_dir", "artifacts")),
            strict_locator_keys=bool(d.get("strict_locator_keys", True)),
            ignore_titlebar_buttons=bool(d.get("ignore_titlebar_buttons", True)),
        )

    def _validate_locator(self, locator: Dict[str, Any], where: str) -> None:
        if not isinstance(locator, dict):
            raise ConfigError(f"{where}: locator must be a dict, got: {type(locator).__name__}")
        if self._app.strict_locator_keys:
            unknown = set(locator.keys()) - ALLOWED_LOCATOR_KEYS
            if unknown:
                raise ConfigError(f"{where}: unknown locator keys: {sorted(unknown)}. Allowed: {sorted(ALLOWED_LOCATOR_KEYS)}")

    def _validate_locators_list(self, locators: Any, where: str) -> List[Dict[str, Any]]:
        if isinstance(locators, dict):
            locators = [locators]
        if not isinstance(locators, list) or not locators:
            raise ConfigError(f"{where}: 'locators' must be a non-empty list")
        for i, loc in enumerate(locators):
            self._validate_locator(loc, f"{where}.locators[{i}]")
        return locators

    def _validate(self) -> None:
        # Validate windows
        if not isinstance(self._windows, dict):
            raise ConfigError("'windows' must be a mapping")
        for wname, wspec in self._windows.items():
            if not isinstance(wspec, dict):
                raise ConfigError(f"windows.{wname} must be a dict")
            locs = wspec.get("locators")
            self._validate_locators_list(locs, f"windows.{wname}")

        # Validate elements
        if not isinstance(self._elements, dict):
            raise ConfigError("'elements' must be a mapping")
        for ename, espec in self._elements.items():
            if not isinstance(espec, dict):
                raise ConfigError(f"elements.{ename} must be a dict")
            if "window" not in espec:
                raise ConfigError(f"elements.{ename} missing required key: 'window'")
            window = espec["window"]
            if not isinstance(window, str) or not window:
                raise ConfigError(f"elements.{ename}.window must be a non-empty string")
            if window not in self._windows:
                raise ConfigError(f"elements.{ename}.window references unknown window '{window}'")
            locs = espec.get("locators")
            self._validate_locators_list(locs, f"elements.{ename}")

    @property
    def app(self) -> AppConfig:
        return self._app

    def get_window_spec(self, name: str) -> Dict[str, Any]:
        if name not in self._windows:
            raise ConfigError(f"Unknown window: {name}")
        return self._windows[name]

    def get_element_spec(self, name: str) -> Dict[str, Any]:
        if name not in self._elements:
            raise ConfigError(f"Unknown element: {name}")
        return self._elements[name]

    def list_windows(self) -> List[str]:
        return sorted(self._windows.keys())

    def list_elements(self) -> List[str]:
        return sorted(self._elements.keys())
