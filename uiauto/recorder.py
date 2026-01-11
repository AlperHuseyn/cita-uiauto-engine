# uiauto/recorder.py
"""
Recording module for capturing user interactions into semantic YAML steps.

Strategy:
---------
Since Windows UIA doesn't provide native event recording APIs, we use a polling-based
approach with pynput for input capture:

1. Listen to mouse clicks and keyboard events via pynput
2. When an action occurs (click/type/hotkey), capture the currently focused UIA element
3. Use inspector logic to extract element info and generate locator candidates
4. Translate interactions into semantic steps (click/type/hotkey)
5. Maintain elements.yaml incrementally with safe merging

Tradeoffs:
----------
- Polling-based: Small lag between action and capture (acceptable for recording)
- Best-effort element identification: May miss transient elements
- QtQuick-friendly: Prefers name/name_re locators (Accessible.name)
- No raw coordinates: All actions mapped to semantic elements
- Keystroke grouping: Consecutive typing on same element merged into single step

Dependencies:
-------------
- pynput: For cross-platform input event capture
- pywinauto: For UIA element inspection
- inspector: For element info extraction and locator generation
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import yaml

try:
    from pynput import keyboard, mouse
except ImportError:
    print("ERROR: pynput not installed. Install with: pip install pynput", file=sys.stderr)
    sys.exit(1)

from pywinauto import Desktop

from .inspector import (
    extract_control_info,
    _normalize_key,
    _make_locator_candidates,
    emit_elements_yaml_stateful,
)


class Recorder:
    """
    Records user interactions and emits semantic scenario YAML + updated elements.yaml.
    
    Usage:
        recorder = Recorder(
            elements_yaml_path="object-maps/elements.yaml",
            window_title_re="MyApp.*",
            state="default"
        )
        recorder.start()
        # User interacts with app
        recorder.stop()
        recorder.save_scenario("scenarios/recorded.yaml")
    """

    def __init__(
        self,
        elements_yaml_path: str,
        scenario_out_path: Optional[str] = None,
        window_title_re: Optional[str] = None,
        window_name: str = "main",
        state: str = "default",
        debug_json_out: Optional[str] = None,
        backend: str = "uia",
    ):
        self.elements_yaml_path = os.path.abspath(elements_yaml_path)
        self.scenario_out_path = scenario_out_path
        self.window_title_re = window_title_re
        self.window_name = window_name
        self.state = state
        self.debug_json_out = debug_json_out
        self.backend = backend

        self.steps: List[Dict[str, Any]] = []
        self.elements_cache: Dict[str, Dict[str, Any]] = {}  # key -> element spec
        self.debug_snapshots: List[Dict[str, Any]] = []
        
        # Typing state tracking
        self._typing_element_key: Optional[str] = None
        self._typing_buffer: List[str] = []
        self._last_action_time = 0.0
        self._typing_timeout = 2.0  # seconds of inactivity to flush typing
        
        # Control flags
        self._recording = False
        self._stop_event = threading.Event()
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None
        
        # Modifier keys state
        self._ctrl_pressed = False
        self._alt_pressed = False
        self._shift_pressed = False
        self._win_pressed = False
        
        self._desktop = Desktop(backend=self.backend)

    def start(self) -> None:
        """Start recording user interactions."""
        print("🎬 Recording started. Interact with the application.")
        print("   Press Ctrl+C in the console to stop recording.")
        self._recording = True
        self._stop_event.clear()
        
        # Start input listeners
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
        )
        
        self._keyboard_listener.start()
        self._mouse_listener.start()
        
        # Start flush checker thread (for typing timeout)
        self._flush_thread = threading.Thread(target=self._flush_checker, daemon=True)
        self._flush_thread.start()

    def stop(self) -> None:
        """Stop recording."""
        if not self._recording:
            return
        
        print("⏹️  Stopping recording...")
        self._recording = False
        self._stop_event.set()
        
        # Flush any pending typing
        self._flush_typing()
        
        # Stop listeners
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()
        
        print(f"✅ Recording stopped. Captured {len(self.steps)} steps.")

    def save_scenario(self, out_path: Optional[str] = None) -> str:
        """Save recorded steps to scenario YAML."""
        out_path = out_path or self.scenario_out_path
        if not out_path:
            raise ValueError("No scenario output path specified")
        
        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        
        scenario = {"steps": self.steps}
        
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(scenario, f, sort_keys=False, allow_unicode=True)
        
        print(f"📝 Scenario saved to: {out_path}")
        return out_path

    def save_elements(self) -> str:
        """Save/merge elements to elements.yaml."""
        # Load existing elements.yaml if it exists
        if os.path.exists(self.elements_yaml_path):
            with open(self.elements_yaml_path, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
        else:
            existing = {}
        
        app_block = existing.get("app", {})
        app_block.setdefault("backend", self.backend)
        
        windows_block = existing.get("windows", {})
        if self.window_name not in windows_block:
            windows_block[self.window_name] = {
                "locators": [{"title_re": self.window_title_re or ".*"}]
            }
        
        elements_block = existing.get("elements", {})
        
        # Merge new elements from cache
        for key, spec in self.elements_cache.items():
            if key not in elements_block:
                elements_block[key] = spec
            else:
                # Element exists - check if state differs
                existing_state = elements_block[key].get("when", {}).get("state")
                if existing_state != self.state:
                    # Create state-specific variant
                    new_key = f"{key}__{self.state}"
                    elements_block[new_key] = spec
                else:
                    # Same state - keep existing (don't overwrite user customizations)
                    pass
        
        final_doc = {
            "app": app_block,
            "windows": windows_block,
            "elements": elements_block,
        }
        
        os.makedirs(os.path.dirname(self.elements_yaml_path) or ".", exist_ok=True)
        with open(self.elements_yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(final_doc, f, sort_keys=False, allow_unicode=True)
        
        print(f"🗺️  Elements saved to: {self.elements_yaml_path}")
        print(f"    Added/updated {len(self.elements_cache)} elements")
        return self.elements_yaml_path

    def save_debug_snapshots(self) -> Optional[str]:
        """Save debug JSON snapshots if enabled."""
        if not self.debug_json_out or not self.debug_snapshots:
            return None
        
        out_path = os.path.abspath(self.debug_json_out)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.debug_snapshots, f, indent=2, ensure_ascii=False)
        
        print(f"🐛 Debug snapshots saved to: {out_path}")
        return out_path

    # =========================================================
    # Event Handlers
    # =========================================================

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """Handle mouse click events."""
        if not self._recording or not pressed:
            return
        
        # Flush any pending typing before processing click
        self._flush_typing()
        
        try:
            # Capture focused element
            element_info = self._capture_focused_element()
            if not element_info:
                return
            
            # Generate element key and ensure it's in elements cache
            elem_key = self._ensure_element(element_info)
            
            # Emit click step
            self.steps.append({"click": {"element": elem_key}})
            self._last_action_time = time.time()
            
            print(f"  🖱️  Click: {elem_key}")
            
        except Exception as e:
            print(f"  ⚠️  Failed to capture click: {e}")

    def _on_key_press(self, key) -> None:
        """Handle key press events."""
        if not self._recording:
            return
        
        try:
            # Track modifier keys
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self._ctrl_pressed = True
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self._alt_pressed = True
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self._shift_pressed = True
            elif key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
                self._win_pressed = True
            
            # Check for hotkey (modifier + regular key)
            if self._ctrl_pressed or self._alt_pressed or self._win_pressed:
                hotkey_str = self._format_hotkey(key)
                if hotkey_str:
                    # Flush any pending typing
                    self._flush_typing()
                    
                    # Emit hotkey step
                    self.steps.append({"hotkey": {"keys": hotkey_str}})
                    self._last_action_time = time.time()
                    
                    print(f"  ⌨️  Hotkey: {hotkey_str}")
                    return
            
            # Handle regular character input (typing)
            char = self._get_char(key)
            if char and not (self._ctrl_pressed or self._alt_pressed or self._win_pressed):
                self._handle_typing(char)
        
        except Exception as e:
            print(f"  ⚠️  Failed to capture key press: {e}")

    def _on_key_release(self, key) -> None:
        """Handle key release events (for modifier tracking)."""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self._ctrl_pressed = False
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self._alt_pressed = False
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self._shift_pressed = False
            elif key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
                self._win_pressed = False
        except Exception:
            pass

    # =========================================================
    # Typing Handling
    # =========================================================

    def _handle_typing(self, char: str) -> None:
        """Handle character typing (buffer for grouping)."""
        try:
            # Capture focused element
            element_info = self._capture_focused_element()
            if not element_info:
                return
            
            # Generate element key
            elem_key = self._ensure_element(element_info)
            
            # If typing on a different element, flush previous buffer
            if self._typing_element_key and self._typing_element_key != elem_key:
                self._flush_typing()
            
            # Append to buffer
            self._typing_element_key = elem_key
            self._typing_buffer.append(char)
            self._last_action_time = time.time()
            
        except Exception as e:
            print(f"  ⚠️  Failed to capture typing: {e}")

    def _flush_typing(self) -> None:
        """Flush accumulated typing buffer into a single type step."""
        if not self._typing_buffer or not self._typing_element_key:
            return
        
        text = "".join(self._typing_buffer)
        self.steps.append({
            "type": {
                "element": self._typing_element_key,
                "text": text
            }
        })
        
        print(f"  ⌨️  Type: {self._typing_element_key} = '{text}'")
        
        # Reset typing state
        self._typing_buffer.clear()
        self._typing_element_key = None

    def _flush_checker(self) -> None:
        """Background thread to flush typing after inactivity timeout."""
        while not self._stop_event.is_set():
            time.sleep(0.5)
            
            if (self._typing_buffer and 
                time.time() - self._last_action_time > self._typing_timeout):
                self._flush_typing()

    # =========================================================
    # Element Capture & Management
    # =========================================================

    def _capture_focused_element(self) -> Optional[Dict[str, Any]]:
        """
        Capture the currently focused UIA element.
        
        Returns element info dict or None if capture failed.
        """
        try:
            # Try to get focused element from desktop
            focused = self._desktop.window()
            
            # Filter by window title if specified
            if self.window_title_re:
                try:
                    window_title = focused.window_text()
                    if not re.search(self.window_title_re, window_title or ""):
                        # Not in target window, ignore
                        return None
                except Exception:
                    pass
            
            # Extract control info using inspector logic
            info = extract_control_info(focused)
            
            # Store debug snapshot if enabled
            if self.debug_json_out:
                self.debug_snapshots.append({
                    "timestamp": time.time(),
                    "element_info": info,
                })
            
            return info
            
        except Exception as e:
            # Failed to capture - this is expected for some transient UI states
            return None

    def _ensure_element(self, element_info: Dict[str, Any]) -> str:
        """
        Ensure element is in elements cache. Returns element key.
        
        Uses inspector normalization rules to generate a stable key.
        If element already exists, reuses existing key.
        """
        # Generate candidates
        candidates = element_info.get("locator_candidates", [])
        if not candidates:
            candidates = _make_locator_candidates(element_info)
        
        # Generate base key from element info
        base_raw = (
            element_info.get("name") or 
            element_info.get("auto_id") or 
            element_info.get("control_type") or 
            "element"
        )
        base_key = _normalize_key(base_raw)
        
        # Check if we already have this element
        # Simple heuristic: if locators match, it's the same element
        for existing_key, existing_spec in self.elements_cache.items():
            existing_locs = existing_spec.get("locators", [])
            if existing_locs and candidates and existing_locs[0] == candidates[0]:
                # Same element, reuse key
                return existing_key
        
        # New element - ensure unique key
        elem_key = base_key
        counter = 1
        while elem_key in self.elements_cache:
            elem_key = f"{base_key}_{counter}"
            counter += 1
        
        # Create element spec
        spec = {
            "window": self.window_name,
            "when": {"state": self.state},
            "locators": candidates[:3],  # Top 3 candidates
        }
        
        self.elements_cache[elem_key] = spec
        return elem_key

    # =========================================================
    # Utilities
    # =========================================================

    def _get_char(self, key) -> Optional[str]:
        """Extract character from key event."""
        try:
            if hasattr(key, "char") and key.char:
                return key.char
            
            # Handle special keys
            if key == keyboard.Key.space:
                return " "
            elif key == keyboard.Key.enter:
                return "\n"
            elif key == keyboard.Key.tab:
                return "\t"
            
            # Ignore other special keys for typing
            return None
            
        except Exception:
            return None

    def _format_hotkey(self, key) -> Optional[str]:
        """
        Format hotkey in pywinauto send_keys format.
        
        Examples:
          Ctrl+L -> "^l"
          Alt+F4 -> "%{F4}"
          Win+R -> "{LWIN}r"
        """
        try:
            # Get key character or name
            if hasattr(key, "char") and key.char:
                key_str = key.char
            elif hasattr(key, "name"):
                key_str = key.name
            else:
                return None
            
            # Don't emit hotkeys for just modifiers
            if key_str in ("ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r", 
                          "shift", "shift_r", "cmd", "cmd_r"):
                return None
            
            # Build modifier prefix
            parts = []
            if self._ctrl_pressed:
                parts.append("^")
            if self._alt_pressed:
                parts.append("%")
            if self._shift_pressed:
                parts.append("+")
            if self._win_pressed:
                parts.append("{LWIN}")
            
            # Special key names for pywinauto
            special_keys = {
                "f1": "{F1}", "f2": "{F2}", "f3": "{F3}", "f4": "{F4}",
                "f5": "{F5}", "f6": "{F6}", "f7": "{F7}", "f8": "{F8}",
                "f9": "{F9}", "f10": "{F10}", "f11": "{F11}", "f12": "{F12}",
                "esc": "{ESC}", "escape": "{ESC}",
                "delete": "{DELETE}", "del": "{DELETE}",
                "backspace": "{BACKSPACE}", "back": "{BACKSPACE}",
                "home": "{HOME}", "end": "{END}",
                "page_up": "{PGUP}", "page_down": "{PGDN}",
                "up": "{UP}", "down": "{DOWN}", "left": "{LEFT}", "right": "{RIGHT}",
            }
            
            key_lower = key_str.lower()
            if key_lower in special_keys:
                key_str = special_keys[key_lower]
            
            return "".join(parts) + key_str
            
        except Exception:
            return None


def record_session(
    elements_yaml: str,
    scenario_out: str,
    window_title_re: Optional[str] = None,
    window_name: str = "main",
    state: str = "default",
    debug_json_out: Optional[str] = None,
) -> Recorder:
    """
    Convenience function to run a recording session.
    
    Returns the Recorder instance for further inspection.
    """
    recorder = Recorder(
        elements_yaml_path=elements_yaml,
        scenario_out_path=scenario_out,
        window_title_re=window_title_re,
        window_name=window_name,
        state=state,
        debug_json_out=debug_json_out,
    )
    
    try:
        recorder.start()
        
        # Wait for user interrupt
        print("\n  Press Ctrl+C to stop recording...\n")
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n")
        recorder.stop()
    
    finally:
        # Save outputs
        if recorder.steps:
            recorder.save_scenario()
            recorder.save_elements()
            if debug_json_out:
                recorder.save_debug_snapshots()
        else:
            print("⚠️  No steps recorded.")
    
    return recorder
