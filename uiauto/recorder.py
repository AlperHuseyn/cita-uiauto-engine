# uiauto/recorder. py
"""
Recording module for capturing user interactions into semantic YAML steps.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

import yaml

try:
    from pynput import keyboard, mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    keyboard = None
    mouse = None

try:
    import comtypes
    import comtypes.client
    try:
        from comtypes.gen import UIAutomationClient as UIA
        UIA_AVAILABLE = True
    except ImportError:
        UIA_AVAILABLE = False
        UIA = None
    COMTYPES_AVAILABLE = True
except ImportError: 
    COMTYPES_AVAILABLE = False
    UIA_AVAILABLE = False
    comtypes = None
    UIA = None

from pywinauto import Desktop

from . inspector import (
    extract_control_info,
    _normalize_key,
    _make_locator_candidates,
    _safe,
)


# Constants
MODIFIER_KEY_NAMES = frozenset([
    "ctrl", "ctrl_l", "ctrl_r",
    "alt", "alt_l", "alt_r", "alt_gr",
    "shift", "shift_l", "shift_r",
    "cmd", "cmd_l", "cmd_r"
])

# Stop hotkey configuration - Default:  Ctrl+Alt+Q
STOP_HOTKEY_CTRL = True
STOP_HOTKEY_ALT = True
STOP_HOTKEY_SHIFT = False
STOP_HOTKEY_KEY = "q"

# Special keys that should be recorded but not as regular typing
SPECIAL_KEYS_MAP = {
    "backspace": "{BACKSPACE}",
    "delete": "{DELETE}",
    "enter": "{ENTER}",
    "return": "{ENTER}",
    "tab": "{TAB}",
    "escape": "{ESC}",
    "esc": "{ESC}",
    "up": "{UP}",
    "down":  "{DOWN}",
    "left": "{LEFT}",
    "right": "{RIGHT}",
    "home": "{HOME}",
    "end": "{END}",
    "page_up": "{PGUP}",
    "page_down":  "{PGDN}",
    "insert": "{INSERT}",
    "f1": "{F1}", "f2": "{F2}", "f3": "{F3}", "f4":  "{F4}",
    "f5": "{F5}", "f6":  "{F6}", "f7": "{F7}", "f8": "{F8}",
    "f9": "{F9}", "f10":  "{F10}", "f11": "{F11}", "f12": "{F12}",
}

# Windows POINT structure for ElementFromPoint
try:
    import ctypes
    from ctypes import wintypes
    
    POINT = wintypes.POINT
    POINT_AVAILABLE = True
    
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        RegisterHotKey = user32.RegisterHotKey
        RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
        RegisterHotKey.restype = wintypes.BOOL
        
        UnregisterHotKey = user32.UnregisterHotKey
        UnregisterHotKey.argtypes = [wintypes.HWND, ctypes. c_int]
        UnregisterHotKey.restype = wintypes. BOOL
        
        CreateWindowEx = user32.CreateWindowExW
        CreateWindowEx.argtypes = [
            wintypes. DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
        ]
        CreateWindowEx.restype = wintypes.HWND
        
        DestroyWindow = user32.DestroyWindow
        DestroyWindow.argtypes = [wintypes.HWND]
        DestroyWindow.restype = wintypes. BOOL
        
        GetModuleHandle = kernel32.GetModuleHandleW
        GetModuleHandle.argtypes = [wintypes. LPCWSTR]
        GetModuleHandle.restype = wintypes. HMODULE
        
        PeekMessage = user32.PeekMessageW
        PeekMessage.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, ctypes. c_uint, ctypes.c_uint, ctypes.c_uint]
        PeekMessage.restype = wintypes. BOOL
        
        TranslateMessage = user32.TranslateMessage
        TranslateMessage.argtypes = [ctypes.POINTER(wintypes. MSG)]
        TranslateMessage.restype = wintypes.BOOL
        
        DispatchMessage = user32.DispatchMessageW
        DispatchMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        DispatchMessage.restype = wintypes. LPARAM
        
        PostQuitMessage = user32.PostQuitMessage
        PostQuitMessage.argtypes = [ctypes.c_int]
        PostQuitMessage.restype = None
        
        SetProcessDPIAware = user32.SetProcessDPIAware
        SetProcessDPIAware.argtypes = []
        SetProcessDPIAware.restype = wintypes.BOOL
        
        VkKeyScanW = user32.VkKeyScanW
        VkKeyScanW.argtypes = [wintypes.WCHAR]
        VkKeyScanW.restype = ctypes.c_short
        
        WINDOWS_API_AVAILABLE = True
    except (AttributeError, OSError):
        WINDOWS_API_AVAILABLE = False
        RegisterHotKey = None
        UnregisterHotKey = None
        CreateWindowEx = None
        DestroyWindow = None
        GetModuleHandle = None
        PeekMessage = None
        TranslateMessage = None
        DispatchMessage = None
        PostQuitMessage = None
        SetProcessDPIAware = None
        VkKeyScanW = None
    
except ImportError:
    POINT = None
    POINT_AVAILABLE = False
    WINDOWS_API_AVAILABLE = False
    RegisterHotKey = None
    UnregisterHotKey = None
    CreateWindowEx = None
    DestroyWindow = None
    GetModuleHandle = None
    PeekMessage = None
    TranslateMessage = None
    DispatchMessage = None
    PostQuitMessage = None
    SetProcessDPIAware = None
    VkKeyScanW = None

# Constants for PeekMessage
PM_REMOVE = 0x0001

# Constants for CreateWindowEx
HWND_MESSAGE = -3

# Hotkey constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

# Recorder constants
MAX_PARENT_WALK_DEPTH = 5


def _print(*args, **kwargs):
    """Print with immediate flush for live output streaming."""
    kwargs.setdefault("flush", True)
    print(*args, **kwargs)


def _get_stop_hotkey_modifiers() -> int:
    """Get Windows modifier flags for stop hotkey."""
    mods = 0
    if STOP_HOTKEY_CTRL:
        mods |= MOD_CONTROL
    if STOP_HOTKEY_ALT:
        mods |= MOD_ALT
    if STOP_HOTKEY_SHIFT: 
        mods |= MOD_SHIFT
    return mods


def _get_stop_hotkey_vk() -> int:
    """Get virtual key code for stop hotkey."""
    if WINDOWS_API_AVAILABLE and VkKeyScanW: 
        result = VkKeyScanW(STOP_HOTKEY_KEY)
        if result != -1:
            return result & 0xFF
    return ord(STOP_HOTKEY_KEY. upper())


def _get_stop_hotkey_display() -> str:
    """Get human-readable stop hotkey string."""
    parts = []
    if STOP_HOTKEY_CTRL:
        parts.append("Ctrl")
    if STOP_HOTKEY_ALT:
        parts.append("Alt")
    if STOP_HOTKEY_SHIFT: 
        parts.append("Shift")
    parts.append(STOP_HOTKEY_KEY. upper())
    return "+".join(parts)


class Recorder:
    """
    Records user interactions and emits semantic scenario YAML + updated elements.yaml.
    """

    def __init__(
        self,
        elements_yaml_path:  str,
        scenario_out_path: Optional[str] = None,
        window_title_re: Optional[str] = None,
        window_name:  str = "main",
        state: str = "default",
        debug_json_out:  Optional[str] = None,
        backend: str = "uia",
        merge:  bool = True,
    ):
        if not PYNPUT_AVAILABLE: 
            raise ImportError(
                "pynput is required for recording but not installed.\n"
                "Install with: pip install pynput"
            )
        
        if not COMTYPES_AVAILABLE: 
            raise ImportError(
                "comtypes is required for recording but not installed.\n"
                "Install with: pip install comtypes"
            )
        
        self.elements_yaml_path = os.path.abspath(elements_yaml_path)
        self.scenario_out_path = scenario_out_path
        self.window_title_re = window_title_re
        self._window_title_rx = re.compile(window_title_re) if window_title_re else None
        self.window_name = window_name
        self.state = state
        self. debug_json_out = debug_json_out
        self. backend = backend
        self.merge = merge

        self.steps: List[Dict[str, Any]] = []
        self. elements_cache: Dict[str, Dict[str, Any]] = {}
        self. debug_snapshots: List[Dict[str, Any]] = []
        
        # Typing state tracking
        self._typing_element_key: Optional[str] = None
        self._typing_buffer: List[str] = []
        self._last_action_time = 0.0
        self._typing_timeout = 2.0
        self._typing_lock = threading.Lock()
        
        # Last clicked element for typing context
        self._last_clicked_element_info: Optional[Dict[str, Any]] = None
        self._last_clicked_element_key: Optional[str] = None
        
        # Control flags
        self._recording = False
        self._stopping = False
        self._stop_requested = False
        self._stop_event = threading.Event()
        self._keyboard_listener:  Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None
        self._hotkey_thread: Optional[threading. Thread] = None
        self._flush_thread: Optional[threading.Thread] = None
        
        # Modifier keys state
        self._ctrl_pressed = False
        self._alt_pressed = False
        self._shift_pressed = False
        self._win_pressed = False
        
        # Stop hotkey state
        self._stop_hotkey_pressed = False
        self._stop_hotkey_id = 1
        self._pending_stop_hotkey = False
        
        # Desktop instance (cached)
        self._desktop:  Optional[Desktop] = None
        
        # Target window cache
        self._target_window = None
        self._target_window_handle = None

    def _get_desktop(self) -> Desktop:
        """Get or create cached Desktop instance."""
        if self._desktop is None:
            self._desktop = Desktop(backend=self.backend)
        return self._desktop

    def _get_target_window(self):
        """Get the target window matching window_title_re."""
        if self._target_window is not None:
            try:
                handle = _safe(lambda: self._target_window. handle)
                if handle == self._target_window_handle:
                    if _safe(lambda: self._target_window. is_visible(), False):
                        return self._target_window
            except Exception:
                pass
            self._target_window = None
            self._target_window_handle = None
        
        desktop = self._get_desktop()
        
        try:
            windows = desktop.windows()
        except Exception:
            windows = []
        
        if not windows:
            return None
        
        visible = []
        for w in windows:
            try:
                if w.is_visible():
                    visible. append(w)
            except Exception: 
                pass
        
        if not visible:
            return None
        
        if self._window_title_rx:
            for w in visible:
                try:
                    title = _safe(w.window_text, "")
                    if self._window_title_rx.search(title or ""):
                        self._target_window = w
                        self._target_window_handle = _safe(lambda: w.handle)
                        return w
                except Exception: 
                    pass
            return None
        
        self._target_window = visible[0]
        self._target_window_handle = _safe(lambda: visible[0].handle)
        return visible[0]

    def start(self) -> None:
        """Start recording user interactions."""
        if WINDOWS_API_AVAILABLE and SetProcessDPIAware:
            try:
                SetProcessDPIAware()
                if self.debug_json_out: 
                    _print("  Debug: DPI awareness enabled")
            except Exception as e:
                if self.debug_json_out:
                    _print(f"  Debug: Failed to enable DPI awareness: {e}")
        
        stop_hotkey_str = _get_stop_hotkey_display()
        _print("🎬 Recording started.  Interact with the application.")
        _print(f"   Press {stop_hotkey_str} to stop recording (or Ctrl+C in console).")
        self._recording = True
        self._stopping = False
        self._stop_requested = False
        self._pending_stop_hotkey = False
        self._stop_event. clear()
        
        if WINDOWS_API_AVAILABLE and RegisterHotKey: 
            self._hotkey_thread = threading.Thread(target=self._hotkey_listener_thread, daemon=True)
            self._hotkey_thread. start()
        
        self._keyboard_listener = keyboard. Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener = mouse. Listener(
            on_click=self._on_mouse_click,
        )
        
        self._keyboard_listener. start()
        self._mouse_listener. start()
        
        self._flush_thread = threading.Thread(target=self._flush_checker, daemon=True)
        self._flush_thread.start()

    def stop(self) -> None:
        """Stop recording."""
        if not self._recording:
            return
        
        _print("⏹️  Stopping recording...")
        self._stopping = True
        self._recording = False
        self._stop_event.set()
        
        self._flush_typing()
        self._remove_stop_hotkey_from_steps()
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._mouse_listener:
            self._mouse_listener. stop()
        
        if WINDOWS_API_AVAILABLE and UnregisterHotKey:
            try:
                UnregisterHotKey(None, self._stop_hotkey_id)
            except Exception: 
                pass
            if PostQuitMessage: 
                try:
                    PostQuitMessage(0)
                except Exception:
                    pass
        
        _print(f"✅ Recording stopped.  Captured {len(self. steps)} steps.")

    def _remove_stop_hotkey_from_steps(self) -> None:
        """Remove any stop hotkey steps that were accidentally recorded."""
        stop_hotkey_parts = []
        if STOP_HOTKEY_CTRL: 
            stop_hotkey_parts.append("^")
        if STOP_HOTKEY_ALT:
            stop_hotkey_parts.append("%")
        if STOP_HOTKEY_SHIFT: 
            stop_hotkey_parts.append("+")
        stop_hotkey_parts.append(STOP_HOTKEY_KEY)
        stop_hotkey_pattern = "".join(stop_hotkey_parts)
        
        alt_patterns = [stop_hotkey_pattern, "^%@", "^%q", "^%Q"]
        
        while self.steps:
            last_step = self. steps[-1]
            if "hotkey" in last_step:
                keys = last_step["hotkey"].get("keys", "")
                if keys in alt_patterns: 
                    self.steps.pop()
                    continue
            break

    def _fix_yaml_list_indent(self, yaml_str: str) -> str:
        """
        Fix YAML list indentation to match desired format.
        
        Converts: 
            locators:
            - name: foo
            control_type: Bar
        
        To:
            locators:
            - name: foo
                control_type:  Bar
        """
        lines = yaml_str. split('\n')
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            
            # Check if this is a list item
            if stripped.startswith('- '):
                # Calculate current indentation
                current_indent = len(line) - len(stripped)
                
                # Add 2 extra spaces to the list item
                result.append(' ' * current_indent + '  ' + stripped)
                
                # Process continuation lines (same dict, more indented than the "- ")
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if not next_line.strip():  # Empty line
                        result.append(next_line)
                        i += 1
                        continue
                    
                    next_stripped = next_line.lstrip()
                    next_indent = len(next_line) - len(next_stripped)
                    
                    # If it's more indented than the list item marker and not a new list item
                    if next_indent > current_indent and not next_stripped.startswith('- '):
                        # Add 2 extra spaces
                        result.append(' ' * next_indent + '  ' + next_stripped)
                        i += 1
                    else:
                        # Not a continuation, break and let outer loop handle it
                        break
            else:
                result. append(line)
                i += 1
        
        return '\n'.join(result)

    def save_scenario(self, out_path: Optional[str] = None) -> str:
        """Save recorded steps to scenario YAML, merging with existing if present."""
        out_path = out_path or self. scenario_out_path
        if not out_path: 
            raise ValueError("No scenario output path specified")
        
        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        
        # Merge with existing scenario if file exists
        existing_steps = []
        if os. path.exists(out_path):
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    existing = yaml.safe_load(f) or {}
                existing_steps = existing.get("steps", [])
                if existing_steps: 
                    _print(f"  📎 Merging with existing scenario ({len(existing_steps)} existing steps)")
            except Exception as e: 
                _print(f"  ⚠️ Could not read existing scenario: {e}")
                existing_steps = []
        
        # Combine existing + new steps
        all_steps = existing_steps + self.steps
        scenario = {"steps": all_steps}
        
        raw_yaml = yaml. safe_dump(scenario, sort_keys=False, allow_unicode=True, default_flow_style=False)
        fixed_yaml = self._fix_yaml_list_indent(raw_yaml)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(fixed_yaml)
        
        _print(f"📝 Scenario saved to:  {out_path}")
        _print(f"    Total steps: {len(all_steps)} ({len(existing_steps)} existing + {len(self. steps)} new)")
        return out_path

    def save_elements(self) -> str:
        """Save/merge elements to elements.yaml."""
        if self.merge and os.path.exists(self.elements_yaml_path):
            with open(self.elements_yaml_path, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
        else:
            existing = {}
        
        app_block = existing.get("app", {})
        app_block. setdefault("backend", self.backend)
        
        windows_block = existing.get("windows", {})
        if self.window_name not in windows_block: 
            title_re = self.window_title_re if self.window_title_re else ".*"
            windows_block[self. window_name] = {
                "locators": [{"title_re": title_re}]
            }
        
        elements_block = existing. get("elements", {})
        
        for key, spec in self.elements_cache.items():
            if key not in elements_block: 
                # Yeni element ekle
                elements_block[key] = spec
            else:
                # Element zaten var - state'e göre karar ver
                existing_state = elements_block[key].get("when", {}).get("state")
                if existing_state != self.state:
                    # Farklı state, yeni key ile ekle
                    new_key = f"{key}__{self.state}"
                    if new_key not in elements_block: 
                        elements_block[new_key] = spec
                # Aynı state ise mevcut elementi koru (kullanıcı değişikliklerini ezme)
        
        final_doc = {
            "app": app_block,
            "windows": windows_block,
            "elements":  elements_block,
        }
        
        os.makedirs(os.path.dirname(self.elements_yaml_path) or ".", exist_ok=True)
        
        raw_yaml = yaml.safe_dump(final_doc, sort_keys=False, allow_unicode=True, default_flow_style=False)
        fixed_yaml = self._fix_yaml_list_indent(raw_yaml)
        
        with open(self.elements_yaml_path, "w", encoding="utf-8") as f:
            f.write(fixed_yaml)
        
        _print(f"🗺️  Elements saved to:  {self.elements_yaml_path}")
        _print(f"    Added/updated {len(self.elements_cache)} elements")
        if self.merge:
            _print(f"    (merged with existing elements)")
        return self.elements_yaml_path

    def save_debug_snapshots(self) -> Optional[str]:
        """Save debug JSON snapshots if enabled."""
        if not self.debug_json_out or not self. debug_snapshots: 
            return None
        
        out_path = os. path.abspath(self.debug_json_out)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.debug_snapshots, f, indent=2, ensure_ascii=False)
        
        _print(f"🐛 Debug snapshots saved to: {out_path}")
        return out_path

    # =========================================================
    # Native Hotkey Listener
    # =========================================================

    def _hotkey_listener_thread(self) -> None:
        """Dedicated thread for listening to native Windows hotkey."""
        if not WINDOWS_API_AVAILABLE or not RegisterHotKey or not PeekMessage:
            return
        
        hwnd = None
        try:
            if CreateWindowEx and GetModuleHandle:
                try:
                    hinstance = GetModuleHandle(None)
                    hwnd = CreateWindowEx(
                        0, "Message", "UIAutoRecorder", 0,
                        0, 0, 0, 0, HWND_MESSAGE, None, hinstance, None
                    )
                    if hwnd and self. debug_json_out:
                        _print(f"  Debug:  Created message-only window (HWND: {hwnd})")
                except Exception as e:
                    if self.debug_json_out:
                        _print(f"  Debug: Failed to create message window: {e}")
                    hwnd = None
            
            hotkey_mods = _get_stop_hotkey_modifiers()
            hotkey_vk = _get_stop_hotkey_vk()
            hotkey_str = _get_stop_hotkey_display()
            
            success = RegisterHotKey(hwnd, self._stop_hotkey_id, hotkey_mods, hotkey_vk)
            
            if not success:
                if self.debug_json_out:
                    _print("  Debug: Failed to register stop hotkey")
                return
            
            if self.debug_json_out:
                _print(f"  Debug: Native stop hotkey registered ({hotkey_str})")
            
            msg = wintypes.MSG()
            while self._recording and not self._stop_event.is_set():
                if PeekMessage(ctypes.byref(msg), hwnd, 0, 0, PM_REMOVE):
                    if msg.message == WM_HOTKEY and msg.wParam == self._stop_hotkey_id: 
                        self._stop_hotkey_pressed = True
                        self._pending_stop_hotkey = True
                        _print(f"\n  🛑 Stop hotkey detected ({hotkey_str})")
                        self._stop_requested = True
                        self._stopping = True
                        self. stop()
                        break
                    else:
                        TranslateMessage(ctypes.byref(msg))
                        DispatchMessage(ctypes.byref(msg))
                else:
                    time.sleep(0.01)
        
        except Exception as e:
            if self.debug_json_out:
                _print(f"  Debug:  Hotkey listener error:  {e}")
        
        finally:
            if WINDOWS_API_AVAILABLE and UnregisterHotKey:
                try: 
                    UnregisterHotKey(hwnd, self._stop_hotkey_id)
                except Exception:
                    pass
            if hwnd and DestroyWindow: 
                try:
                    DestroyWindow(hwnd)
                    if self.debug_json_out: 
                        _print("  Debug:  Destroyed message window")
                except Exception: 
                    pass

    # =========================================================
    # Event Handlers
    # =========================================================

    def _on_mouse_click(self, x: int, y:  int, button: mouse.Button, pressed: bool) -> None:
        """Handle mouse click events."""
        if not self._recording or not pressed or self._stopping or self._stop_requested:
            return
        
        self._flush_typing()
        
        try:
            time. sleep(0.05)
            
            element_info = None
            for attempt in range(3):
                element_info = self._capture_element_at_point(x, y)
                if element_info:
                    break
                time. sleep(0.05)
            
            if not element_info: 
                if self.debug_json_out: 
                    _print(f"  Debug:  Click at ({x}, {y}): Could not identify element")
                _print(f"  ⚠️  Click:  Could not identify element at ({x}, {y})")
                return
            
            elem_key = self._ensure_element(element_info)
            
            self._last_clicked_element_info = element_info
            self._last_clicked_element_key = elem_key
            
            self. steps.append({"click": {"element": elem_key}})
            self._last_action_time = time.time()
            
            _print(f"  🖱️  Click: {elem_key}")
            
        except Exception as e: 
            if self.debug_json_out: 
                _print(f"  Debug: Failed to capture click: {type(e).__name__}: {e}")
            _print(f"  ⚠️  Failed to capture click: {e}")

    def _on_key_press(self, key) -> None:
        """Handle key press events."""
        if self._stop_requested or self._pending_stop_hotkey:
            return
        
        if not self._recording or self._stopping:
            return
        
        try:
            key_name = self._get_key_name(key)
            
            # Track modifier keys
            if key_name in ("ctrl_l", "ctrl_r", "ctrl"):
                self._ctrl_pressed = True
                return
            elif key_name in ("alt_l", "alt_r", "alt", "alt_gr"):
                self._alt_pressed = True
                return
            elif key_name in ("shift", "shift_l", "shift_r"):
                self._shift_pressed = True
                return
            elif key_name in ("cmd", "cmd_l", "cmd_r"):
                self._win_pressed = True
                return
            
            # Check if this is the stop hotkey
            if self._is_stop_hotkey(key_name):
                self._pending_stop_hotkey = True
                return
            
            # Check for hotkeys (Ctrl/Alt/Win + key, NOT just Shift)
            if self._ctrl_pressed or self._alt_pressed or self._win_pressed:
                if self._is_stop_hotkey_variant(key_name):
                    self._pending_stop_hotkey = True
                    return
                
                hotkey_str = self._format_hotkey(key)
                if hotkey_str:
                    self._flush_typing()
                    self. steps.append({"hotkey": {"keys": hotkey_str}})
                    self._last_action_time = time.time()
                    _print(f"  ⌨️  Hotkey: {hotkey_str}")
                    return
            
            # Handle special keys (backspace, enter, etc.)
            if key_name in SPECIAL_KEYS_MAP:
                self._handle_special_key(key_name)
                return
            
            # Handle regular character input (including uppercase with Shift)
            char = self._get_char(key)
            if char:
                self._handle_typing(char)
        
        except Exception as e:
            if self.debug_json_out:
                _print(f"  Debug: Failed to capture key press: {type(e).__name__}: {e}")

    def _on_key_release(self, key) -> None:
        """Handle key release events (for modifier tracking)."""
        try:
            key_name = self._get_key_name(key)
            
            if key_name in ("ctrl_l", "ctrl_r", "ctrl"):
                self._ctrl_pressed = False
            elif key_name in ("alt_l", "alt_r", "alt", "alt_gr"):
                self._alt_pressed = False
            elif key_name in ("shift", "shift_l", "shift_r"):
                self._shift_pressed = False
            elif key_name in ("cmd", "cmd_l", "cmd_r"):
                self._win_pressed = False
        except Exception: 
            pass

    def _get_key_name(self, key) -> str:
        """Get normalized key name from pynput key object."""
        try:
            if hasattr(key, 'name') and key.name:
                return key. name. lower()
            elif hasattr(key, 'char') and key.char:
                return key.char.lower()
            return ""
        except Exception: 
            return ""

    def _is_stop_hotkey(self, key_name: str) -> bool:
        """Check if current key press with modifiers matches stop hotkey."""
        if STOP_HOTKEY_CTRL != self._ctrl_pressed:
            return False
        if STOP_HOTKEY_ALT != self._alt_pressed:
            return False
        if STOP_HOTKEY_SHIFT != self._shift_pressed:
            return False
        return key_name == STOP_HOTKEY_KEY. lower()

    def _is_stop_hotkey_variant(self, key_name:  str) -> bool:
        """Check if current key could be a stop hotkey variant."""
        if not (self._ctrl_pressed and self._alt_pressed):
            return False
        if key_name == STOP_HOTKEY_KEY.lower():
            return True
        if key_name == "@" and STOP_HOTKEY_KEY.lower() == "q":
            return True
        return False

    # =========================================================
    # Typing Handling
    # =========================================================

    def _handle_typing(self, char: str) -> None:
        """Handle character typing (buffer for grouping)."""
        try:
            element_info = self._capture_focused_element()
            
            if not element_info and self._last_clicked_element_info:
                element_info = self._last_clicked_element_info
                if self. debug_json_out:
                    _print("  Debug: Using last clicked element as typing target")
            
            if not element_info: 
                if self.debug_json_out: 
                    _print(f"  Debug:  Typing '{char}' but could not identify focused element")
                return
            
            elem_key = self._ensure_element(element_info)
            
            with self._typing_lock:
                if self._typing_element_key and self._typing_element_key != elem_key: 
                    self._flush_typing_unsafe()
                
                self._typing_element_key = elem_key
                self._typing_buffer. append(char)
                self._last_action_time = time.time()
            
        except Exception as e: 
            if self. debug_json_out:
                _print(f"  Debug:  Failed to capture typing:  {type(e).__name__}: {e}")

    def _handle_special_key(self, key_name: str) -> None:
        """Handle special keys like backspace, enter, etc."""
        try:
            special_key_str = SPECIAL_KEYS_MAP. get(key_name)
            if not special_key_str:
                return
            
            element_info = self._capture_focused_element()
            if not element_info and self._last_clicked_element_info: 
                element_info = self._last_clicked_element_info
            
            if not element_info:
                if self.debug_json_out: 
                    _print(f"  Debug: Special key '{key_name}' but could not identify focused element")
                return
            
            elem_key = self._ensure_element(element_info)
            
            with self._typing_lock:
                if self._typing_element_key == elem_key: 
                    self._typing_buffer.append(special_key_str)
                else:
                    self._flush_typing_unsafe()
                    self._typing_element_key = elem_key
                    self._typing_buffer. append(special_key_str)
                self._last_action_time = time.time()
            
            if self.debug_json_out:
                _print(f"  Debug: Special key:  {key_name} -> {special_key_str}")
            
        except Exception as e:
            if self.debug_json_out:
                _print(f"  Debug: Failed to handle special key: {type(e).__name__}: {e}")

    def _flush_typing(self) -> None:
        """Flush accumulated typing buffer into a single type step (thread-safe)."""
        with self._typing_lock:
            self._flush_typing_unsafe()

    def _flush_typing_unsafe(self) -> None:
        """Flush typing buffer without acquiring lock (must be called with lock held)."""
        if not self._typing_buffer or not self._typing_element_key: 
            return
        
        text = "".join(self._typing_buffer)
        self.steps.append({
            "type":  {
                "element": self._typing_element_key,
                "text": text
            }
        })
        
        _print(f"  ⌨️  Type: {self._typing_element_key} = '{text}'")
        
        self._typing_buffer. clear()
        self._typing_element_key = None

    def _flush_checker(self) -> None:
        """Background thread to flush typing after inactivity timeout."""
        while not self._stop_event.is_set():
            time.sleep(0.5)
            with self._typing_lock:
                if self._typing_buffer and time.time() - self._last_action_time > self._typing_timeout:
                    self._flush_typing_unsafe()

    # =========================================================
    # Element Capture & Management
    # =========================================================

    def _capture_focused_element(self) -> Optional[Dict[str, Any]]: 
        """Capture the currently focused UIA element."""
        try:
            target_window = self._get_target_window()
            if not target_window:
                return None
            
            try:
                descendants = target_window.descendants()
            except Exception:
                return None
            
            for ctrl in descendants:
                try:
                    elem_info = ctrl.element_info
                    if hasattr(elem_info, 'has_keyboard_focus') and elem_info.has_keyboard_focus: 
                        info = extract_control_info(ctrl)
                        if self.debug_json_out:
                            self.debug_snapshots.append({
                                "timestamp": time.time(),
                                "type": "focus",
                                "element_info": info,
                            })
                        return info
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            if self.debug_json_out:
                _print(f"  Debug: Failed to capture focused element: {type(e).__name__}: {e}")
            return None

    def _capture_element_at_point(self, x: int, y:  int) -> Optional[Dict[str, Any]]:
        """Capture the UIA element at the specified screen coordinates."""
        try:
            target_window = self._get_target_window()
            if not target_window:
                return None
            
            try:
                rect = target_window. rectangle()
                if not (rect. left <= x <= rect.right and rect. top <= y <= rect.bottom):
                    if self.debug_json_out:
                        _print(f"  Debug: Click at ({x}, {y}) outside target window bounds")
                    return None
            except Exception:
                pass
            
            element = None
            try:
                desktop = self._get_desktop()
                element = desktop.from_point(x, y)
            except Exception as e:
                if self.debug_json_out:
                    _print(f"  Debug: from_point failed: {type(e).__name__}: {e}")
            
            if element is None:
                element = self._find_element_at_point_in_descendants(target_window, x, y)
            
            if element is None:
                return None
            
            refined = self._refine_element(element)
            info = extract_control_info(refined)
            
            if self.debug_json_out:
                raw_info = extract_control_info(element) if element != refined else None
                self.debug_snapshots.append({
                    "timestamp": time.time(),
                    "type": "click",
                    "coordinates": {"x": x, "y": y},
                    "raw_element_info": raw_info,
                    "refined_element_info": info,
                })
            
            return info
            
        except Exception as e:
            if self.debug_json_out:
                _print(f"  Debug: Failed to capture element at point: {type(e).__name__}: {e}")
            return None

    def _find_element_at_point_in_descendants(self, window, x:  int, y: int):
        """Find element at point by searching through window descendants."""
        try:
            descendants = window.descendants()
        except Exception:
            return None
        
        best_match = None
        best_area = float('inf')
        
        for ctrl in descendants: 
            try:
                rect = ctrl.rectangle()
                if rect.left <= x <= rect.right and rect.top <= y <= rect.bottom:
                    area = (rect.right - rect.left) * (rect.bottom - rect.top)
                    if area < best_area:
                        best_area = area
                        best_match = ctrl
            except Exception: 
                continue
        
        return best_match

    def _refine_element(self, element) -> Any:
        """Walk up the parent chain to find the most meaningful element."""
        generic_types = {"Pane", "Custom", "Group", "Window", "", None}
        current = element
        
        for depth in range(MAX_PARENT_WALK_DEPTH):
            try:
                control_type = _safe(lambda c=current: c.element_info.control_type, "")
                name = _safe(lambda c=current: c.element_info. name, "")
                
                if name and control_type and control_type not in generic_types: 
                    return current
                
                parent = _safe(lambda c=current: c.parent())
                if parent is None:
                    break
                
                parent_handle = _safe(lambda p=parent: p. handle)
                current_handle = _safe(lambda c=current: c. handle)
                
                if parent_handle is None or parent_handle == current_handle:
                    break
                
                current = parent
                
            except Exception:
                break
        
        return element

    def _ensure_element(self, element_info: Dict[str, Any]) -> str:
        """Ensure element is in elements cache.  Returns element key."""
        candidates = element_info.get("locator_candidates", [])
        if not candidates:
            candidates = _make_locator_candidates(element_info)
        
        base_raw = (
            element_info.get("name") or
            element_info.get("auto_id") or
            element_info.get("control_type") or
            "element"
        )
        base_key = _normalize_key(base_raw)
        
        if not base_key: 
            base_key = "element"
        
        for existing_key, existing_spec in self.elements_cache.items():
            existing_locs = existing_spec. get("locators", [])
            if existing_locs and candidates and existing_locs[0] == candidates[0]: 
                return existing_key
        
        elem_key = base_key
        counter = 1
        while elem_key in self.elements_cache:
            elem_key = f"{base_key}_{counter}"
            counter += 1
        
        spec = {
            "window": self.window_name,
            "when": {"state": self.state},
            "locators": candidates[: 3],
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
                return key. char
            return None
        except Exception: 
            return None

    def _format_hotkey(self, key) -> Optional[str]: 
        """Format hotkey in pywinauto send_keys format."""
        try:
            if hasattr(key, "char") and key.char:
                key_str = key.char
            elif hasattr(key, "name") and key.name:
                key_str = key.name
            else: 
                return None
            
            if key_str. lower() in MODIFIER_KEY_NAMES:
                return None
            
            parts = []
            if self._ctrl_pressed:
                parts.append("^")
            if self._alt_pressed:
                parts.append("%")
            # Only add Shift if combined with Ctrl/Alt/Win
            if self._shift_pressed and (self._ctrl_pressed or self._alt_pressed or self._win_pressed):
                parts. append("+")
            if self._win_pressed:
                parts. append("{LWIN}")
            
            special_keys = {
                "f1": "{F1}", "f2": "{F2}", "f3": "{F3}", "f4":  "{F4}",
                "f5": "{F5}", "f6":  "{F6}", "f7": "{F7}", "f8": "{F8}",
                "f9": "{F9}", "f10":  "{F10}", "f11": "{F11}", "f12": "{F12}",
                "esc": "{ESC}", "escape": "{ESC}",
                "delete": "{DELETE}", "del": "{DELETE}",
                "backspace": "{BACKSPACE}", "back": "{BACKSPACE}",
                "home": "{HOME}", "end": "{END}",
                "page_up": "{PGUP}", "page_down": "{PGDN}",
                "up": "{UP}", "down": "{DOWN}", "left": "{LEFT}", "right": "{RIGHT}",
            }
            
            key_lower = key_str. lower()
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
    merge: bool = True,  # Yeni parametre
) -> Recorder:
    """
    Convenience function to run a recording session.
    
    Args:
        elements_yaml: Path to elements.yaml file
        scenario_out: Path to output scenario YAML
        window_title_re: Optional regex to filter target window
        window_name:  Window name in elements.yaml (default: "main")
        state: UI state name for recorded elements (default: "default")
        debug_json_out: Optional path for debug JSON snapshots
        merge:  If True, merge with existing elements. yaml (default: True)
    
    Returns the Recorder instance for further inspection.
    """
    recorder = Recorder(
        elements_yaml_path=elements_yaml,
        scenario_out_path=scenario_out,
        window_title_re=window_title_re,
        window_name=window_name,
        state=state,
        debug_json_out=debug_json_out,
        merge=merge,
    )
    
    stop_hotkey_str = _get_stop_hotkey_display()
    
    try:
        recorder. start()
        
        _print(f"\n  Press {stop_hotkey_str} to stop recording (or Ctrl+C in console)...\n")
        while recorder._recording:
            time.sleep(0.5)
        
        if recorder._stop_hotkey_pressed: 
            time.sleep(0.5)
    
    except KeyboardInterrupt: 
        _print("\n")
        recorder._stop_requested = True
        recorder.stop()
    
    finally:
        if recorder.steps:
            recorder.save_scenario()
            recorder. save_elements()
            if debug_json_out:
                recorder.save_debug_snapshots()
        else:
            _print("⚠️  No steps recorded.")
    
    return recorder