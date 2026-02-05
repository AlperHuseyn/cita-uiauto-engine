# uiauto_ui/utils/platform.py
"""
Platform-specific utilities.
Handles Windows/Linux/macOS differences.
"""

import os
import sys
import platform
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PlatformInfo:
    """Platform information."""
    system: str           # Windows, Linux, Darwin
    release: str          # OS version
    python_version: str   # Python version
    architecture: str     # 64bit, 32bit
    is_windows: bool
    is_linux: bool
    is_macos: bool
    encoding: str         # Preferred encoding


def get_platform_info() -> PlatformInfo:
    """
    Get comprehensive platform information.
    
    Returns:
        PlatformInfo with current platform details
    """
    system = platform.system()
    return PlatformInfo(
        system=system,
        release=platform.release(),
        python_version=platform.python_version(),
        architecture=platform.architecture()[0],
        is_windows=(system == "Windows"),
        is_linux=(system == "Linux"),
        is_macos=(system == "Darwin"),
        encoding=get_encoding(),
    )


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"


def get_encoding() -> str:
    """
    Get the preferred encoding for subprocess output.
    
    Returns:
        Encoding string (utf-8 preferred, falls back to system default)
    """
    # Always prefer UTF-8, but be aware of Windows quirks
    if is_windows():
        # Windows console might use cp1252 or other codepage
        # But we force UTF-8 in subprocess calls
        return "utf-8"
    return "utf-8"


def get_subprocess_env() -> Dict[str, str]:
    """
    Get environment variables for subprocess execution.
    
    Returns:
        Environment dict with encoding settings
    """
    env = os.environ.copy()
    
    # Force UTF-8 encoding
    env["PYTHONIOENCODING"] = "utf-8"
    
    if is_windows():
        # Ensure UTF-8 mode on Windows
        env["PYTHONUTF8"] = "1"
    
    return env


def get_python_executable() -> str:
    """
    Get the Python executable path.
    
    Returns:
        Path to Python executable
    """
    return sys.executable


def get_startupinfo():
    """
    Get subprocess startupinfo for Windows.
    
    Returns:
        subprocess.STARTUPINFO or None
    """
    if is_windows():
        import subprocess
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo
    return None