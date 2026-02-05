# uiauto_ui/utils/paths.py
"""
Path utilities for the UI application.
Handles frozen (PyInstaller) vs development paths.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def is_frozen() -> bool:
    """
    Check if running as a frozen (PyInstaller) application.
    
    Returns:
        True if frozen, False if running from source
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_bundle_dir() -> Path:
    """
    Get the bundle directory (where resources are located).
    
    For frozen apps, this is the temp extraction directory.
    For development, this is the package directory.
    
    Returns:
        Path to bundle directory
    """
    if is_frozen():
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).parent.parent


def get_app_dir() -> Path:
    """
    Get the application directory (where the executable is).
    
    Returns:
        Path to application directory
    """
    if is_frozen():
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


def get_app_data_dir() -> Path:
    """
    Get the application data directory for user settings and logs.
    
    Windows: %APPDATA%/cita/uiauto-ui
    Linux: ~/.config/cita/uiauto-ui
    macOS: ~/Library/Application Support/cita/uiauto-ui
    
    Returns:
        Path to app data directory (created if needed)
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    
    app_data = base / "cita" / "uiauto-ui"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data


def get_log_file_path() -> Path:
    """
    Get the path to the application log file.
    
    Returns:
        Path to log file
    """
    return get_app_data_dir() / "uiauto-ui.log"


def get_settings_path() -> Path:
    """
    Get the path to the settings file.
    
    Returns:
        Path to settings file
    """
    return get_app_data_dir() / "settings.json"


def get_resource_path(relative_path: str) -> Path:
    """
    Get the path to a bundled resource file.
    
    Args:
        relative_path: Path relative to resources directory
        
    Returns:
        Absolute path to resource
    """
    return get_bundle_dir() / "resources" / relative_path


def resolve_path(path: str, base_dir: Optional[Path] = None) -> Path:
    """
    Resolve a path, handling relative paths and environment variables.
    
    Args:
        path: Path string (may be relative or contain env vars)
        base_dir: Base directory for relative paths (default: cwd)
        
    Returns:
        Resolved absolute path
    """
    # Expand environment variables and user home
    expanded = os.path.expandvars(os.path.expanduser(path))
    path_obj = Path(expanded)
    
    if path_obj.is_absolute():
        return path_obj
    
    if base_dir is None:
        base_dir = Path.cwd()
    
    return (base_dir / path_obj).resolve()


def ensure_parent_exists(path: Path) -> Path:
    """
    Ensure the parent directory of a path exists.
    
    Args:
        path: File path
        
    Returns:
        The same path (for chaining)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    return path