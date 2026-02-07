# uiauto_ui/services/settings_service.py
"""
Settings persistence service using QSettings.
Handles last-used paths, window geometry, and preferences.
"""

from typing import Optional, List, Any
from pathlib import Path

from PySide6.QtCore import QSettings, QByteArray

from ..utils.logging import get_logger

logger = get_logger(__name__)


class SettingsService:
    """
    Service for persisting user settings.
    
    Uses QSettings for platform-appropriate storage:
    - Windows: Registry (HKEY_CURRENT_USER/Software/cita/uiauto-ui)
    - Linux: ~/.config/cita/uiauto-ui.conf
    - macOS: ~/Library/Preferences/com.cita.uiauto-ui.plist
    
    Settings categories:
    - paths: Last used file paths
    - window: Window geometry and state
    - ui: UI preferences
    """
    
    # Settings keys
    KEY_WINDOW_GEOMETRY = "window/geometry"
    KEY_WINDOW_STATE = "window/state"
    KEY_SPLITTER_STATE = "window/splitter_state"
    KEY_LAST_TAB = "window/last_tab"
    
    KEY_LAST_ELEMENTS = "paths/last_elements"
    KEY_LAST_SCENARIO = "paths/last_scenario"
    KEY_LAST_SCENARIOS_DIR = "paths/last_scenarios_dir"
    KEY_LAST_REPORT = "paths/last_report"
    KEY_LAST_APP = "paths/last_app"
    KEY_LAST_OUT_DIR = "paths/last_out_dir"
    KEY_LAST_EMIT_YAML = "paths/last_emit_yaml"
    KEY_LAST_SCENARIO_OUT = "paths/last_scenario_out"
    
    KEY_RECENT_ELEMENTS = "recent/elements"
    KEY_RECENT_SCENARIOS = "recent/scenarios"
    
    KEY_VERBOSE_DEFAULT = "ui/verbose_default"
    KEY_CI_MODE_DEFAULT = "ui/ci_mode_default"
    KEY_THEME = "ui/theme"
    KEY_SCENARIO_MODE = "ui/scenario_mode"
    
    MAX_RECENT_FILES = 10
    
    def __init__(self):
        self._settings = QSettings("cita", "uiauto-ui")
        logger.debug(f"Settings file: {self._settings.fileName()}")
    
    # -------------------------------------------------------------------------
    # Window State
    # -------------------------------------------------------------------------
    
    def save_window_geometry(self, geometry: QByteArray) -> None:
        """Save window geometry."""
        self._settings.setValue(self.KEY_WINDOW_GEOMETRY, geometry)
    
    def load_window_geometry(self) -> Optional[QByteArray]:
        """Load window geometry."""
        value = self._settings.value(self.KEY_WINDOW_GEOMETRY)
        return value if isinstance(value, QByteArray) else None
    
    def save_window_state(self, state: QByteArray) -> None:
        """Save window state (toolbars, docks, etc.)."""
        self._settings.setValue(self.KEY_WINDOW_STATE, state)
    
    def load_window_state(self) -> Optional[QByteArray]:
        """Load window state."""
        value = self._settings.value(self.KEY_WINDOW_STATE)
        return value if isinstance(value, QByteArray) else None
    
    def save_splitter_state(self, state: QByteArray) -> None:
        """Save splitter position."""
        self._settings.setValue(self.KEY_SPLITTER_STATE, state)
    
    def load_splitter_state(self) -> Optional[QByteArray]:
        """Load splitter position."""
        value = self._settings.value(self.KEY_SPLITTER_STATE)
        return value if isinstance(value, QByteArray) else None
    
    def save_last_tab(self, index: int) -> None:
        """Save last active tab index."""
        self._settings.setValue(self.KEY_LAST_TAB, index)
    
    def load_last_tab(self) -> int:
        """Load last active tab index."""
        return int(self._settings.value(self.KEY_LAST_TAB, 0))
    
    # -------------------------------------------------------------------------
    # Path Settings
    # -------------------------------------------------------------------------
    
    def save_path(self, key: str, path: str) -> None:
        """Save a path setting."""
        if path and path.strip():
            self._settings.setValue(key, path)
    
    def load_path(self, key: str, default: str = "") -> str:
        """Load a path setting."""
        return str(self._settings.value(key, default))
    
    # Convenience methods for common paths
    
    def save_last_elements(self, path: str) -> None:
        self.save_path(self.KEY_LAST_ELEMENTS, path)
        self._add_recent(self.KEY_RECENT_ELEMENTS, path)
    
    def load_last_elements(self) -> str:
        return self.load_path(self.KEY_LAST_ELEMENTS)
    
    def save_last_scenario(self, path: str) -> None:
        self.save_path(self.KEY_LAST_SCENARIO, path)
        self._add_recent(self.KEY_RECENT_SCENARIOS, path)
    
    def load_last_scenario(self) -> str:
        return self.load_path(self.KEY_LAST_SCENARIO)
    
    def save_last_scenarios_dir(self, path: str) -> None:
        self.save_path(self.KEY_LAST_SCENARIOS_DIR, path)

    def load_last_scenarios_dir(self) -> str:
        return self.load_path(self.KEY_LAST_SCENARIOS_DIR)
    
    def save_last_report(self, path: str) -> None:
        self.save_path(self.KEY_LAST_REPORT, path)
    
    def load_last_report(self) -> str:
        return self.load_path(self.KEY_LAST_REPORT, "report.json")
    
    def save_last_app(self, path: str) -> None:
        self.save_path(self.KEY_LAST_APP, path)
    
    def load_last_app(self) -> str:
        return self.load_path(self.KEY_LAST_APP)
    
    def save_last_out_dir(self, path: str) -> None:
        self.save_path(self.KEY_LAST_OUT_DIR, path)
    
    def load_last_out_dir(self) -> str:
        return self.load_path(self.KEY_LAST_OUT_DIR, "reports")
    
    def save_last_emit_yaml(self, path: str) -> None:
        self.save_path(self.KEY_LAST_EMIT_YAML, path)
    
    def load_last_emit_yaml(self) -> str:
        return self.load_path(self.KEY_LAST_EMIT_YAML)
    
    def save_last_scenario_out(self, path: str) -> None:
        self.save_path(self.KEY_LAST_SCENARIO_OUT, path)
    
    def load_last_scenario_out(self) -> str:
        return self.load_path(self.KEY_LAST_SCENARIO_OUT)
    
    # -------------------------------------------------------------------------
    # Recent Files
    # -------------------------------------------------------------------------
    
    def _add_recent(self, key: str, path: str) -> None:
        """Add a path to the recent files list."""
        recent = self.load_recent(key)
        
        # Remove if already exists
        if path in recent:
            recent.remove(path)
        
        # Add to front
        recent.insert(0, path)
        
        # Limit size
        recent = recent[:self.MAX_RECENT_FILES]
        
        self._settings.setValue(key, recent)
    
    def load_recent(self, key: str) -> List[str]:
        """Load recent files list."""
        value = self._settings.value(key, [])
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            return [value] if value else []
        return []
    
    def get_recent_elements(self) -> List[str]:
        return self.load_recent(self.KEY_RECENT_ELEMENTS)
    
    def get_recent_scenarios(self) -> List[str]:
        return self.load_recent(self.KEY_RECENT_SCENARIOS)
    
    # -------------------------------------------------------------------------
    # UI Preferences
    # -------------------------------------------------------------------------
    
    def save_verbose_default(self, enabled: bool) -> None:
        self._settings.setValue(self.KEY_VERBOSE_DEFAULT, enabled)
    
    def load_verbose_default(self) -> bool:
        return bool(self._settings.value(self.KEY_VERBOSE_DEFAULT, False))
    
    def save_ci_mode_default(self, enabled: bool) -> None:
        self._settings.setValue(self.KEY_CI_MODE_DEFAULT, enabled)
    
    def load_ci_mode_default(self) -> bool:
        return bool(self._settings.value(self.KEY_CI_MODE_DEFAULT, False))
    
    def save_theme(self, theme: str) -> None:
        self._settings.setValue(self.KEY_THEME, theme)
    
    def load_theme(self) -> str:
        return str(self._settings.value(self.KEY_THEME, "dark"))

    def save_last_scenario_mode(self, mode: str) -> None:
        self._settings.setValue(self.KEY_SCENARIO_MODE, mode)

    def load_last_scenario_mode(self) -> str:
        return str(self._settings.value(self.KEY_SCENARIO_MODE, "single"))
    
    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------
    
    def clear_all(self) -> None:
        """Clear all settings."""
        self._settings.clear()
        logger.info("All settings cleared")
    
    def sync(self) -> None:
        """Force sync settings to storage."""
        self._settings.sync()