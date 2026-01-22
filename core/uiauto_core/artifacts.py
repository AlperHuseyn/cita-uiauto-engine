# core/uiauto_core/artifacts.py
"""
Generic artifact generation utilities (screenshots, dumps).
Framework-specific implementations should override these.
"""
from __future__ import annotations
import os
import time
from typing import Any, Dict, Optional, Callable


def _ts() -> str:
    """Generate timestamp string for file naming."""
    return time.strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: str) -> None:
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def make_artifacts(
    window: Any,
    out_dir: str,
    prefix: str,
    capture_func: Optional[Callable[[Any, str, str], Optional[str]]] = None,
    dump_func: Optional[Callable[[Any, str, str], Optional[str]]] = None,
) -> Dict[str, str]:
    """
    Generic artifact generation function.
    
    @param window Window object (framework-specific)
    @param out_dir Output directory
    @param prefix File prefix
    @param capture_func Optional framework-specific screenshot capture function
    @param dump_func Optional framework-specific tree dump function
    @return Dict of artifact types to file paths
    """
    artifacts: Dict[str, str] = {}
    
    if capture_func:
        try:
            img = capture_func(window, out_dir, prefix + "_screenshot")
            if img:
                artifacts["screenshot"] = img
        except Exception:
            pass
    
    if dump_func:
        try:
            tree = dump_func(window, out_dir, prefix + "_tree")
            if tree:
                artifacts["tree"] = tree
        except Exception:
            pass
    
    return artifacts
