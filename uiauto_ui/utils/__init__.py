# uiauto_ui/utils/__init__.py
"""
Utility modules for cita-uiauto-engine GUI.
"""

from .logging import setup_logging, get_logger
from .paths import (
    is_frozen,
    get_bundle_dir,
    get_app_dir,
    get_app_data_dir,
    get_log_file_path,
    get_resource_path,
)
from .platform import (
    is_windows,
    is_linux,
    is_macos,
    get_platform_info,
    get_subprocess_env,
    get_python_executable,
    get_startupinfo,
)

__all__ = [
    # logging
    "setup_logging",
    "get_logger",
    # paths
    "is_frozen",
    "get_bundle_dir",
    "get_app_dir",
    "get_app_data_dir",
    "get_log_file_path",
    "get_resource_path",
    # platform
    "is_windows",
    "is_linux",
    "is_macos",
    "get_platform_info",
    "get_subprocess_env",
    "get_python_executable",
    "get_startupinfo",
]