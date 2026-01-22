# javafx/uiauto_javafx/inspector.py
"""JavaFX UI inspector using Java Access Bridge."""

from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, List, Optional

from .jab_bridge import JABBridge


def _ts() -> str:
    """Generate timestamp string."""
    return time.strftime("%Y%m%d_%H%M%S")


def inspect_window(
    jvm_path: Optional[str] = None,
    window_title: Optional[str] = None,
    max_depth: int = 10,
    include_invisible: bool = False,
) -> Dict[str, Any]:
    """
    Inspect JavaFX window and enumerate accessible elements.
    
    Args:
        jvm_path: Optional path to JVM
        window_title: Window title to inspect (or None for first window)
        max_depth: Maximum tree traversal depth
        include_invisible: Include invisible elements
        
    Returns:
        Dict with window and element information
    """
    bridge = JABBridge(jvm_path=jvm_path)
    
    # Find window
    if window_title:
        window = bridge.get_window_by_title(window_title, exact=False)
        if not window:
            raise RuntimeError(f"Window not found: {window_title}")
    else:
        windows = bridge.get_all_windows()
        if not windows:
            raise RuntimeError("No visible windows found")
        window = windows[0]
    
    # Get window info
    try:
        w_title = str(window.getTitle()) if hasattr(window, 'getTitle') else str(window.getName())
    except Exception:
        w_title = "Unknown"
    
    result = {
        "window_title": w_title,
        "timestamp": _ts(),
        "controls": [],
    }
    
    # Get accessible context
    window_context = bridge.get_accessible_context(window)
    if not window_context:
        return result
    
    # Traverse tree and collect elements
    def visitor(context):
        try:
            info = bridge.get_element_info(context)
            
            # Filter invisible if requested
            if not include_invisible and not info.get("visible"):
                return False
            
            # Add to results
            result["controls"].append(info)
        except Exception:
            pass
        return False  # Continue traversal
    
    bridge._traverse_tree(window_context, visitor, max_depth=max_depth)
    
    return result


def write_inspect_outputs(result: Dict[str, Any], out_dir: str = "reports") -> Dict[str, str]:
    """
    Write inspection results to files.
    
    Args:
        result: Inspection result dict
        out_dir: Output directory
        
    Returns:
        Dict mapping output type to file path
    """
    os.makedirs(out_dir, exist_ok=True)
    
    timestamp = result.get("timestamp", _ts())
    window_title = result.get("window_title", "window").replace(" ", "_")
    
    paths = {}
    
    # Write JSON
    json_path = os.path.join(out_dir, f"inspect_{window_title}_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    paths["json"] = json_path
    
    # Write text summary
    txt_path = os.path.join(out_dir, f"inspect_{window_title}_{timestamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"JavaFX Window Inspection\n")
        f.write(f"=" * 80 + "\n")
        f.write(f"Window: {result.get('window_title')}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Controls: {len(result.get('controls', []))}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, ctrl in enumerate(result.get("controls", []), 1):
            f.write(f"[{i}] {ctrl.get('role', 'UNKNOWN')}\n")
            f.write(f"    name: {ctrl.get('name')!r}\n")
            f.write(f"    description: {ctrl.get('description')!r}\n")
            f.write(f"    text: {ctrl.get('text')!r}\n")
            f.write(f"    visible: {ctrl.get('visible')}\n")
            f.write(f"    enabled: {ctrl.get('enabled')}\n")
            f.write(f"    children: {ctrl.get('child_count', 0)}\n")
            f.write("\n")
    
    paths["text"] = txt_path
    
    return paths


def emit_elements_yaml(
    result: Dict[str, Any],
    out_path: str,
    window_name: str = "main",
) -> str:
    """
    Generate elements.yaml from inspection results.
    
    Args:
        result: Inspection result dict
        out_path: Output YAML file path
        window_name: Window name to use in YAML
        
    Returns:
        Path to generated YAML file
    """
    import yaml
    
    window_title = result.get("window_title", "")
    controls = result.get("controls", [])
    
    # Build YAML structure
    data = {
        "app": {
            "backend": "jab",
            "default_timeout": 10.0,
            "polling_interval": 0.2,
        },
        "windows": {
            window_name: {
                "locators": [{"title": window_title}]
            }
        },
        "elements": {}
    }
    
    # Generate element specs for visible, named controls
    element_count = 0
    for ctrl in controls:
        if not ctrl.get("visible"):
            continue
        
        name = ctrl.get("name")
        role = ctrl.get("role")
        
        if not name or not role:
            continue
        
        # Create element name
        element_name = name.lower().replace(" ", "_")
        if element_name in data["elements"]:
            element_name = f"{element_name}_{element_count}"
        
        # Add element spec
        data["elements"][element_name] = {
            "window": window_name,
            "locators": [
                {
                    "name": name,
                    "control_type": role,
                }
            ]
        }
        element_count += 1
    
    # Write YAML
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
    
    return out_path
