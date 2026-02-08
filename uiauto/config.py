# uiauto/config.py
"""
@file config.py
@brief Centralized timeout and retry configuration for the framework.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

from .timings import (PAUSE_FIELDS, TIMEOUT_FIELDS, build_preset_values, list_presets)


@dataclass
class TimeoutSettings:
    """Individual timeout settings for a specific operation type."""
    timeout: float
    interval: float
    retry_count: Optional[int] = None
    
    def with_overrides(
        self,
        timeout: Optional[float] = None,
        interval: Optional[float] = None,
        retry_count: Optional[int] = None,
    ) -> TimeoutSettings:
        """Create a new settings instance with overrides applied."""
        return TimeoutSettings(
            timeout=timeout if timeout is not None else self.timeout,
            interval=interval if interval is not None else self.interval,
            retry_count=retry_count if retry_count is not None else self.retry_count,
        )


class TimeConfig:
    """
    Global timeout configuration for the framework.
    
    Usage:
        # Modify global defaults
        TimeConfig.default().element_wait.timeout = 15.0
        
        # Use context manager for temporary overrides
        with TimeConfig.override(element_wait=TimeoutSettings(5.0, 0.1)):
            actions.click("fast_element")
    """
    
    _default_instance: Optional[TimeConfig] = None
    _default_preset: str = "default"
    _local = threading.local()
    _lock = threading.Lock()
    
    def __init__(self, preset: Optional[str] = None):
        preset_name = preset or self._default_preset
        self._apply_values(build_preset_values(preset_name))

    @classmethod
    def _timeout_fields(cls) -> Dict[str, Dict[str, Any]]:
        return TIMEOUT_FIELDS

    @classmethod
    def _pause_fields(cls) -> Dict[str, float]:
        return PAUSE_FIELDS

    def _apply_values(self, values: Dict[str, Any]) -> None:
        for name in self._timeout_fields():
            val = values.get(name)
            if isinstance(val, TimeoutSettings):
                setting = deepcopy(val)
            elif isinstance(val, dict):
                setting = TimeoutSettings(
                    timeout=float(val["timeout"]),
                    interval=float(val["interval"]),
                    retry_count=val.get("retry_count"),
                )
            else:
                raise ValueError(f"Invalid timeout setting for {name}: {val}")
            setattr(self, name, setting)

        for name in self._pause_fields():
            if name not in values:
                raise ValueError(f"Missing pause setting for {name}")
            setattr(self, name, float(values[name]))

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for name in self._timeout_fields():
            setting: TimeoutSettings = getattr(self, name)
            data[name] = {
                "timeout": setting.timeout,
                "interval": setting.interval,
                "retry_count": setting.retry_count,
            }
        for name in self._pause_fields():
            data[name] = getattr(self, name)
        return data

    def _clone(self) -> TimeConfig:
        clone = TimeConfig()
        clone._apply_values(self.to_dict())
        return clone

    def get_action_settings(self, action_name: str) -> TimeoutSettings:
        mapping = {
            "click": "click_action",
            "double_click": "double_click_action",
            "right_click": "right_click_action",
            "hover": "hover_action",
            "set_text": "set_text_action",
            "get_text": "get_text_action",
            "check": "check_action",
            "uncheck": "uncheck_action",
            "select": "select_action",
            "select_item": "select_item_action",
            "key_send": "key_send_action",
        }
        field = mapping.get(action_name)
        if field and hasattr(self, field):
            return getattr(self, field)
        return self.action_timeout
        
    @classmethod
    def default(cls) -> TimeConfig:
        """Get the global default configuration (singleton)."""
        if cls._default_instance is None:
            with cls._lock:
                if cls._default_instance is None:
                    cls._default_instance = cls(cls._default_preset)
        return cls._default_instance
    
    @classmethod
    def current(cls) -> TimeConfig:
        """Get the current effective configuration."""
        override = getattr(cls._local, "override", None)
        if override is not None:
            return override
        return cls.default()
    
    @classmethod
    def apply_preset(cls, preset: str) -> None:
        """Apply a timing preset to the global configuration."""
        values = build_preset_values(preset)
        config = cls.default()
        config._apply_values(values)
        cls._default_preset = preset

    @classmethod
    def apply_overrides(cls, overrides: Dict[str, Any]) -> None:
        """Apply overrides to the global configuration."""
        config = cls.default()
        _apply_overrides(config, overrides)

    @classmethod
    def apply_timeout_override(cls, timeout: float) -> None:
        """Override base timeout values without changing intervals."""
        config = cls.default()
        base_overrides: Dict[str, Any] = {
            "element_wait": {"timeout": timeout},
            "window_wait": {"timeout": timeout * 2},
            "visibility_wait": {"timeout": timeout},
            "enabled_wait": {"timeout": timeout / 2},
            "resolve_window": {"timeout": timeout},
            "resolve_element": {"timeout": timeout},
            "wait_for_any": {"timeout": timeout},
            "exists_wait": {"timeout": max(timeout / 5, 0.1)},
        }
        _apply_overrides(config, base_overrides)

    @classmethod
    def apply_app_defaults(cls, default_timeout: float, polling_interval: float) -> None:
        """Apply elements.yaml default_timeout/polling_interval to base waits."""
        config = cls.default()
        app_overrides: Dict[str, Any] = {
            "element_wait": {"timeout": default_timeout, "interval": polling_interval},
            "visibility_wait": {"timeout": default_timeout, "interval": polling_interval},
            "enabled_wait": {"timeout": default_timeout, "interval": polling_interval},
            "resolve_window": {"timeout": default_timeout, "interval": polling_interval},
            "resolve_element": {"timeout": default_timeout, "interval": polling_interval},
            "wait_for_any": {"timeout": default_timeout, "interval": polling_interval},
            "exists_wait": {"timeout": max(default_timeout / 5, polling_interval), "interval": polling_interval},
        }
        _apply_overrides(config, app_overrides)
    
    @classmethod
    @contextmanager
    def override(cls, **kwargs: Any) -> Generator[TimeConfig, None, None]:
        """Context manager for temporary configuration overrides."""
        previous = getattr(cls._local, "override", None)
        new_config = cls.current()._clone()
        _apply_overrides(new_config, kwargs)
        
        cls._local.override = new_config
        try:
            yield new_config
        finally:
            cls._local.override = previous
    
    @classmethod
    def reset_to_defaults(cls) -> None:
        """Reset global configuration to factory defaults."""
        with cls._lock:
            cls._default_preset = "default"
            cls._default_instance = cls(cls._default_preset)
        cls._local.override = None

def _apply_overrides(config: TimeConfig, overrides: Dict[str, Any]) -> None:
    for key, value in overrides.items():
        if key in config._timeout_fields():
            base_setting: TimeoutSettings = getattr(config, key)
            if isinstance(value, TimeoutSettings):
                setattr(config, key, deepcopy(value))
            elif isinstance(value, dict):
                new_setting = base_setting.with_overrides(
                    timeout=value.get("timeout"),
                    interval=value.get("interval"),
                    retry_count=value.get("retry_count"),
                )
                setattr(config, key, new_setting)
            else:
                raise ValueError(f"Invalid override for {key}: {value}")
        elif key in config._pause_fields():
            setattr(config, key, float(value))
        else:
            raise ValueError(f"Unknown TimeConfig field: {key}")

def configure_for_ci() -> None:
    """Configure timeouts optimized for CI/CD environments."""
    TimeConfig.apply_preset("ci")

def configure_for_local_dev() -> None:
    """Configure timeouts optimized for local development."""
    TimeConfig.apply_preset("fast")

def configure_for_slow() -> None:
    """Configure timeouts optimized for slow environments."""
    TimeConfig.apply_preset("slow")

def available_presets() -> Dict[str, Dict[str, Any]]:
    return list_presets()