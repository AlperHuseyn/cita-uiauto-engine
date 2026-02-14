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

from .timings import (PAUSE_FIELDS, TIMEOUT_FIELDS, build_preset_values,
                      list_presets)


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
    Timeout configuration for the framework.

    Deterministic precedence is applied per run via build/install APIs:
      base defaults -> preset -> CLI overrides -> app defaults
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

    def clone(self) -> TimeConfig:
        """Return a deep clone of this config."""
        clone = TimeConfig()
        clone._apply_values(self.to_dict())
        return clone

    def _clone(self) -> TimeConfig:
        return self.clone()

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
    def build_from(
        cls,
        *,
        preset: str = "default",
        overrides: Optional[Dict[str, Any]] = None,
        app_defaults: Optional[Dict[str, float]] = None,
    ) -> TimeConfig:
        """Build a deterministic run-scope config snapshot."""
        cfg = cls(preset)
        if overrides:
            _apply_overrides(cfg, overrides)
        if app_defaults and preset == "default":
            default_timeout = float(app_defaults["default_timeout"])
            polling_interval = float(app_defaults["polling_interval"])
            _apply_overrides(
                cfg,
                {
                    "element_wait": {"timeout": default_timeout, "interval": polling_interval},
                    "visibility_wait": {"timeout": default_timeout, "interval": polling_interval},
                    "enabled_wait": {"timeout": default_timeout, "interval": polling_interval},
                    "resolve_window": {"timeout": default_timeout, "interval": polling_interval},
                    "resolve_element": {"timeout": default_timeout, "interval": polling_interval},
                    "wait_for_any": {"timeout": default_timeout, "interval": polling_interval},
                    "exists_wait": {
                        "timeout": max(default_timeout / 5, polling_interval),
                        "interval": polling_interval,
                    },
                },
            )
        return cfg

    @classmethod
    def default(cls) -> TimeConfig:
        """Get the immutable process default configuration (singleton)."""
        if cls._default_instance is None:
            with cls._lock:
                if cls._default_instance is None:
                    cls._default_instance = cls(cls._default_preset)
        return cls._default_instance
    
    @classmethod
    def install_run_config(cls, config: TimeConfig) -> None:
        """Install per-thread run configuration snapshot."""
        cls._local.run_config = config

    @classmethod
    def clear_run_config(cls) -> None:
        """Clear per-thread run configuration snapshot."""
        cls._local.run_config = None

    @classmethod
    def current(cls) -> TimeConfig:
        """Get the current effective configuration."""
        run_cfg = getattr(cls._local, "run_config", None)
        if run_cfg is not None:
            return run_cfg

        override = getattr(cls._local, "override", None)
        if override is not None:
            return override

        return cls.default()
    
    @classmethod
    def apply_preset(cls, preset: str) -> None:
        """Backward-compatible API: apply preset to current run-scope config."""
        base = cls.current().clone()
        base._apply_values(build_preset_values(preset))
        cls.install_run_config(base)

    @classmethod
    def apply_overrides(cls, overrides: Dict[str, Any]) -> None:
        """Backward-compatible API: apply overrides to current run-scope config."""
        config = cls.current().clone()
        _apply_overrides(config, overrides)
        cls.install_run_config(config)

    @classmethod
    def apply_timeout_override(cls, timeout: float) -> None:
        """Backward-compatible API: override base timeout values for run-scope config."""
        config = cls.current().clone()
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
        cls.install_run_config(config)

    @classmethod
    def apply_app_defaults(cls, default_timeout: float, polling_interval: float) -> None:
        """Backward-compatible API: apply app defaults to run-scope config."""
        config = cls.current().clone()
        app_overrides: Dict[str, Any] = {
            "element_wait": {"timeout": default_timeout, "interval": polling_interval},
            "visibility_wait": {"timeout": default_timeout, "interval": polling_interval},
            "enabled_wait": {"timeout": default_timeout, "interval": polling_interval},
            "resolve_window": {"timeout": default_timeout, "interval": polling_interval},
            "resolve_element": {"timeout": default_timeout, "interval": polling_interval},
            "wait_for_any": {"timeout": default_timeout, "interval": polling_interval},
            "exists_wait": {
                "timeout": max(default_timeout / 5, polling_interval),
                "interval": polling_interval,
            },
        }
        _apply_overrides(config, app_overrides)
        cls.install_run_config(config)

    
    @classmethod
    @contextmanager
    def override(cls, **kwargs: Any) -> Generator[TimeConfig, None, None]:
        """Context manager for temporary configuration overrides."""
        previous = getattr(cls._local, "override", None)
        new_config = cls.current().clone()
        _apply_overrides(new_config, kwargs)
        
        cls._local.override = new_config
        try:
            yield new_config
        finally:
            cls._local.override = previous
    
    @classmethod
    def reset_to_defaults(cls) -> None:
        """Reset default and clear all thread-local config state."""
        with cls._lock:
            cls._default_preset = "default"
            cls._default_instance = cls(cls._default_preset)
        cls._local.override = None
        cls._local.run_config = None

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
    """Configure timeouts optimized for CI/CD environments (run scope)."""
    TimeConfig.apply_preset("ci")

def configure_for_local_dev() -> None:
    """Configure timeouts optimized for local development (run scope)."""
    TimeConfig.apply_preset("fast")

def configure_for_slow() -> None:
    """Configure timeouts optimized for slow environments (run scope)."""
    TimeConfig.apply_preset("slow")

def available_presets() -> Dict[str, Dict[str, Any]]:
    return list_presets()