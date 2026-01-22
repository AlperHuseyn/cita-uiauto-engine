# javafx/uiauto_javafx/inspector.py
"""JavaFX inspector for analyzing UI elements."""
from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, List, Optional


def inspect_javafx_window(
    bridge,
    window_context: Any,
    max_controls: int = 3000,
    include_invisible: bool = False,
) -> Dict[str, Any]:
    """
    Inspect JavaFX window and generate element candidates.
    
    @param bridge JAB bridge instance
    @param window_context Window AccessibleContext to inspect
    @param max_controls Maximum number of controls to scan
    @param include_invisible Include invisible controls
    @return Dict with inspection results
    """
    controls = []
    
    def traverse(ctx, depth=0, path=""):
        """Recursively traverse accessibility tree."""
        if depth > 15 or len(controls) >= max_controls or ctx is None:
            return
        
        try:
            info = bridge.get_element_info(ctx)
            
            # Filter invisible if requested
            if not include_invisible and not info.get("visible", False):
                return
            
            # Build control record
            control = {
                "name": info.get("name", ""),
                "role": info.get("role", ""),
                "description": info.get("description", ""),
                "visible": info.get("visible", False),
                "enabled": info.get("enabled", False),
                "focusable": info.get("focusable", False),
                "states": info.get("states", []),
                "child_count": info.get("child_count", 0),
                "depth": depth,
                "path": path,
            }
            
            controls.append(control)
            
            # Traverse children
            child_count = ctx.getAccessibleChildrenCount()
            for i in range(min(child_count, 50)):  # Limit children per node
                child = ctx.getAccessibleChild(i)
                if child:
                    child_ctx = child.getAccessibleContext()
                    if child_ctx:
                        child_path = f"{path}/{i}"
                        traverse(child_ctx, depth + 1, child_path)
        except Exception as e:
            # Log but continue
            pass
    
    traverse(window_context, 0, "0")
    
    return {
        "controls": controls,
        "total_count": len(controls),
        "timestamp": time.time(),
    }


def write_inspect_outputs(result: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    """
    Write inspection results to files.
    
    @param result Inspection result dict
    @param out_dir Output directory
    @return Dict of output file paths
    """
    os.makedirs(out_dir, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Write JSON
    json_path = os.path.join(out_dir, f"inspect_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    # Write human-readable text
    txt_path = os.path.join(out_dir, f"inspect_{timestamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("JavaFX UI Inspection Report\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total Controls: {result['total_count']}\n\n")
        
        for i, ctrl in enumerate(result.get("controls", []), 1):
            f.write(f"[{i}] {ctrl.get('role', 'Unknown')}\n")
            f.write(f"    Name: {ctrl.get('name', '')}\n")
            f.write(f"    Description: {ctrl.get('description', '')}\n")
            f.write(f"    Visible: {ctrl.get('visible', False)}\n")
            f.write(f"    Enabled: {ctrl.get('enabled', False)}\n")
            f.write(f"    Depth: {ctrl.get('depth', 0)}\n")
            f.write(f"    Path: {ctrl.get('path', '')}\n")
            f.write("\n")
    
    return {
        "json": json_path,
        "txt": txt_path,
    }
