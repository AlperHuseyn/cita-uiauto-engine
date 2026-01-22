# qtquick/uiauto_qtquick/artifacts.py
from __future__ import annotations
import os
import time
from typing import Dict, Optional

from PIL import ImageGrab


def _ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def capture_window_image(window, out_dir: str, name_prefix: str) -> Optional[str]:
    """
    Try to capture a pywinauto window as an image.
    Returns file path or None if capture fails.
    """
    ensure_dir(out_dir)
    path = os.path.join(out_dir, f"{name_prefix}_{_ts()}.png")

    # 1) preferred: pywinauto wrapper capture
    try:
        img = window.capture_as_image()
        img.save(path)
        return path
    except Exception:
        pass

    # 2) fallback: ImageGrab of rectangle
    try:
        rect = window.rectangle()
        bbox = (rect.left, rect.top, rect.right, rect.bottom)
        img = ImageGrab.grab(bbox=bbox)
        img.save(path)
        return path
    except Exception:
        return None


def dump_control_identifiers(window, out_dir: str, name_prefix: str) -> Optional[str]:
    """
    Dumps control identifiers to a text file, including element_info.name for QtQuick support.
    """
    ensure_dir(out_dir)
    path = os.path.join(out_dir, f"{name_prefix}_{_ts()}.txt")
    try:
        # First, write standard print_control_identifiers output
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            window.print_control_identifiers()
        txt = buf.getvalue()
        
        # Append additional element_info.name data for QtQuick debugging
        buf_enhanced = io.StringIO()
        buf_enhanced.write(txt)
        buf_enhanced.write("\n\n")
        buf_enhanced.write("=" * 80 + "\n")
        buf_enhanced.write("Enhanced dump with element_info.name (for QtQuick debugging):\n")
        buf_enhanced.write("=" * 80 + "\n\n")
        
        try:
            descendants = window.descendants()
            for i, ctrl in enumerate(descendants[:100]):  # Limit to first 100 for performance
                try:
                    ctrl_type = ctrl.element_info.control_type
                    elem_name = getattr(ctrl.element_info, 'name', '')
                    auto_id = ctrl.element_info.automation_id
                    window_text = ctrl.window_text()
                    visible = ctrl.is_visible()
                    
                    buf_enhanced.write(f"[{i}] {ctrl_type}\n")
                    buf_enhanced.write(f"    element_info.name: {elem_name!r}\n")
                    buf_enhanced.write(f"    automation_id: {auto_id!r}\n")
                    buf_enhanced.write(f"    window_text: {window_text!r}\n")
                    buf_enhanced.write(f"    visible: {visible}\n")
                    buf_enhanced.write("\n")
                except Exception as e:
                    buf_enhanced.write(f"[{i}] Error: {e}\n\n")
        except Exception as e:
            buf_enhanced.write(f"Could not enumerate descendants: {e}\n")
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(buf_enhanced.getvalue())
        return path
    except Exception:
        return None


def make_artifacts(window, out_dir: str, prefix: str) -> Dict[str, str]:
    """
    Returns dict like {"screenshot": "...", "tree": "..."} (only those that succeed).
    """
    artifacts: Dict[str, str] = {}
    img = capture_window_image(window, out_dir, prefix + "_screenshot")
    if img:
        artifacts["screenshot"] = img
    tree = dump_control_identifiers(window, out_dir, prefix + "_tree")
    if tree:
        artifacts["tree"] = tree
    return artifacts
