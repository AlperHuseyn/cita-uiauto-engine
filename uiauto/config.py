# uiauto/config.py
"""
@file config.py
@brief Centralized timeout and retry configuration for the framework.
"""

from __future__ import annotations
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional
from copy import deepcopy


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
        retry_count: Optional[int] = None
    ) -> TimeoutSettings:
        """Create a new settings instance with overrides applied."""
        return TimeoutSettings(
            timeout=timeout if timeout is not None else self.timeout,
            interval=interval if interval is not None else self.interval,
            retry_count=retry_count if retry_count is not None else self.retry_count
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
    _local = threading.local()
    _lock = threading.Lock()
    
    def __init__(self):
        self.element_wait = TimeoutSettings(timeout=10.0, interval=0.2)
        self.window_wait = TimeoutSettings(timeout=30.0, interval=0.5)
        self.action_timeout = TimeoutSettings(timeout=5.0, interval=0.2, retry_count=3)
        self.visibility_wait = TimeoutSettings(timeout=10.0, interval=0.2)
        self.enabled_wait = TimeoutSettings(timeout=5.0, interval=0.2)
        self.disappear_wait = TimeoutSettings(timeout=60.0, interval=0.5)
        self.staleness_retry = TimeoutSettings(timeout=5.0, interval=0.3, retry_count=3)
    
    @classmethod
    def default(cls) -> TimeConfig:
        """Get the global default configuration (singleton)."""
        if cls._default_instance is None:
            with cls._lock:
                if cls._default_instance is None:
                    cls._default_instance = cls()
        return cls._default_instance
    
    @classmethod
    def current(cls) -> TimeConfig:
        """Get the current effective configuration."""
        override = getattr(cls._local, 'override', None)
        if override is not None:
            return override
        return cls.default()
    
    @classmethod
    @contextmanager
    def override(cls, **kwargs: Any) -> Generator[TimeConfig, None, None]:
        """Context manager for temporary configuration overrides."""
        previous = getattr(cls._local, 'override', None)
        
        new_config = cls()
        current = cls.current()
        # Copy current values
        new_config.element_wait = current.element_wait
        new_config.window_wait = current.window_wait
        new_config.action_timeout = current.action_timeout
        new_config.visibility_wait = current.visibility_wait
        new_config.enabled_wait = current.enabled_wait
        new_config.disappear_wait = current.disappear_wait
        new_config.staleness_retry = current.staleness_retry
        
        # Apply overrides
        for key, value in kwargs.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
            else:
                raise ValueError(f"Unknown TimeConfig field: {key}")
        
        cls._local.override = new_config
        try:
            yield new_config
        finally:
            cls._local.override = previous
    
    @classmethod
    def reset_to_defaults(cls) -> None:
        """Reset global configuration to factory defaults."""
        with cls._lock:
            cls._default_instance = cls()
        cls._local.override = None


def configure_for_ci() -> None:
    """Configure timeouts optimized for CI/CD environments."""
    config = TimeConfig.default()
    config.element_wait = TimeoutSettings(timeout=20.0, interval=0.3)
    config.window_wait = TimeoutSettings(timeout=60.0, interval=1.0)
    config.action_timeout = TimeoutSettings(timeout=10.0, interval=0.3, retry_count=5)
    config.disappear_wait = TimeoutSettings(timeout=120.0, interval=1.0)


def configure_for_local_dev() -> None:
    """Configure timeouts optimized for local development."""
    config = TimeConfig.default()
    config.element_wait = TimeoutSettings(timeout=5.0, interval=0.1)
    config.window_wait = TimeoutSettings(timeout=15.0, interval=0.3)
    config.action_timeout = TimeoutSettings(timeout=3.0, interval=0.1, retry_count=2)
    config.disappear_wait = TimeoutSettings(timeout=30.0, interval=0.3)