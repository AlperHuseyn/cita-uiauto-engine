# core/uiauto_core/artifacts.py
"""Generic artifact generation interface for screenshots and reports."""

from __future__ import annotations
import os
import time
from typing import Any, Dict, Optional


def _ts() -> str:
    """Generate timestamp string for filenames."""
    return time.strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: str) -> None:
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def make_artifacts(window: Any, out_dir: str, prefix: str, capture_func=None, dump_func=None) -> Dict[str, str]:
    """
    Generic artifact generation with pluggable capture functions.
    
    Args:
        window: Window object (framework-specific)
        out_dir: Output directory for artifacts
        prefix: Filename prefix
        capture_func: Optional custom capture function(window, out_dir, prefix) -> Optional[str]
        dump_func: Optional custom dump function(window, out_dir, prefix) -> Optional[str]
        
    Returns:
        Dict mapping artifact type to file path
    """
    artifacts: Dict[str, str] = {}
    
    if capture_func:
        img = capture_func(window, out_dir, prefix + "_screenshot")
        if img:
            artifacts["screenshot"] = img
    
    if dump_func:
        tree = dump_func(window, out_dir, prefix + "_tree")
        if tree:
            artifacts["tree"] = tree
    
    return artifacts
