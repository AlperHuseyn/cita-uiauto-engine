# uiauto/timings.py
"""
@file timings.py
@brief Time configuration presets and defaults for UI automation.
"""

from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict


TIMEOUT_FIELDS: Dict[str, Dict[str, Any]] = {
    "element_wait": {"timeout": 10.0, "interval": 0.2},
    "window_wait": {"timeout": 30.0, "interval": 0.5},
    "action_timeout": {"timeout": 5.0, "interval": 0.2, "retry_count": 3},
    "visibility_wait": {"timeout": 10.0, "interval": 0.2},
    "enabled_wait": {"timeout": 5.0, "interval": 0.2},
    "disappear_wait": {"timeout": 60.0, "interval": 0.5},
    "staleness_retry": {"timeout": 5.0, "interval": 0.3, "retry_count": 3},
    "resolve_window": {"timeout": 10.0, "interval": 0.2},
    "resolve_element": {"timeout": 10.0, "interval": 0.2},
    "child_window_quick": {"timeout": 1.5, "interval": 0.2},
    "exists_wait": {"timeout": 2.0, "interval": 0.1},
    "wait_for_any": {"timeout": 10.0, "interval": 0.2},
    "wait_for_idle": {"timeout": 5.0, "interval": 0.2},
    "app_start": {"timeout": 30.0, "interval": 0.5},
    "app_connect": {"timeout": 10.0, "interval": 0.2},
    "app_close": {"timeout": 5.0, "interval": 0.2},
    "window_close": {"timeout": 5.0, "interval": 0.2},
    "window_open": {"timeout": 10.0, "interval": 0.2},
    "menu_open": {"timeout": 2.0, "interval": 0.1},
    "tooltip_wait": {"timeout": 2.0, "interval": 0.1},
    "drag_drop": {"timeout": 5.0, "interval": 0.2},
    "hover_wait": {"timeout": 1.0, "interval": 0.1},
    "focus_wait": {"timeout": 2.0, "interval": 0.1},
    "select_wait": {"timeout": 5.0, "interval": 0.2},
    "select_item_wait": {"timeout": 5.0, "interval": 0.2},
    "combo_open_wait": {"timeout": 2.0, "interval": 0.1},
    "combo_select_wait": {"timeout": 5.0, "interval": 0.2},
    "check_wait": {"timeout": 3.0, "interval": 0.1},
    "uncheck_wait": {"timeout": 3.0, "interval": 0.1},
    "set_text_wait": {"timeout": 5.0, "interval": 0.2},
    "get_text_wait": {"timeout": 3.0, "interval": 0.1},
    "click_action": {"timeout": 5.0, "interval": 0.2, "retry_count": 3},
    "double_click_action": {"timeout": 5.0, "interval": 0.2, "retry_count": 3},
    "right_click_action": {"timeout": 5.0, "interval": 0.2, "retry_count": 3},
    "hover_action": {"timeout": 3.0, "interval": 0.2, "retry_count": 2},
    "set_text_action": {"timeout": 5.0, "interval": 0.2, "retry_count": 3},
    "get_text_action": {"timeout": 3.0, "interval": 0.2, "retry_count": 2},
    "check_action": {"timeout": 3.0, "interval": 0.2, "retry_count": 2},
    "uncheck_action": {"timeout": 3.0, "interval": 0.2, "retry_count": 2},
    "select_action": {"timeout": 5.0, "interval": 0.2, "retry_count": 2},
    "select_item_action": {"timeout": 5.0, "interval": 0.2, "retry_count": 2},
    "key_send_action": {"timeout": 2.0, "interval": 0.1, "retry_count": 2},
    "clipboard_wait": {"timeout": 2.0, "interval": 0.1},
    "screenshot_wait": {"timeout": 2.0, "interval": 0.1},
    "highlight_wait": {"timeout": 1.0, "interval": 0.1},
    "cache_refresh": {"timeout": 2.0, "interval": 0.1},
}

PAUSE_FIELDS: Dict[str, float] = {
    "after_click_pause": 0.1,
    "after_double_click_pause": 0.05,
    "after_right_click_pause": 0.05,
    "after_type_pause": 0.05,
    "combo_open_pause": 0.2,
    "combo_select_pause": 0.2,
    "hotkey_pause": 0.05,
    "drag_drop_pause": 0.1,
    "hover_pause": 0.05,
    "focus_pause": 0.05,
}

PRESET_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "fast": {
        "element_wait": {"timeout": 5.0, "interval": 0.1},
        "window_wait": {"timeout": 15.0, "interval": 0.3},
        "action_timeout": {"timeout": 3.0, "interval": 0.1, "retry_count": 2},
        "visibility_wait": {"timeout": 6.0, "interval": 0.1},
        "enabled_wait": {"timeout": 3.0, "interval": 0.1},
        "disappear_wait": {"timeout": 30.0, "interval": 0.3},
        "staleness_retry": {"timeout": 3.0, "interval": 0.2, "retry_count": 2},
        "child_window_quick": {"timeout": 1.0, "interval": 0.1},
        "exists_wait": {"timeout": 1.0, "interval": 0.05},
        "wait_for_any": {"timeout": 6.0, "interval": 0.1},
        "app_start": {"timeout": 20.0, "interval": 0.4},
        "window_close": {"timeout": 3.0, "interval": 0.1},
        "after_click_pause": 0.05,
        "after_double_click_pause": 0.03,
        "after_right_click_pause": 0.03,
        "combo_open_pause": 0.1,
        "combo_select_pause": 0.1,
        "hotkey_pause": 0.03,
    },
    "slow": {
        "element_wait": {"timeout": 20.0, "interval": 0.3},
        "window_wait": {"timeout": 60.0, "interval": 0.6},
        "action_timeout": {"timeout": 8.0, "interval": 0.3, "retry_count": 4},
        "visibility_wait": {"timeout": 20.0, "interval": 0.3},
        "enabled_wait": {"timeout": 10.0, "interval": 0.3},
        "disappear_wait": {"timeout": 90.0, "interval": 0.7},
        "staleness_retry": {"timeout": 8.0, "interval": 0.4, "retry_count": 4},
        "exists_wait": {"timeout": 4.0, "interval": 0.2},
        "wait_for_any": {"timeout": 15.0, "interval": 0.3},
        "app_start": {"timeout": 45.0, "interval": 0.8},
        "window_close": {"timeout": 8.0, "interval": 0.3},
        "after_click_pause": 0.15,
        "after_double_click_pause": 0.08,
        "after_right_click_pause": 0.08,
        "combo_open_pause": 0.3,
        "combo_select_pause": 0.3,
        "hotkey_pause": 0.08,
    },
    "ci": {
        "element_wait": {"timeout": 20.0, "interval": 0.3},
        "window_wait": {"timeout": 60.0, "interval": 1.0},
        "action_timeout": {"timeout": 10.0, "interval": 0.3, "retry_count": 5},
        "visibility_wait": {"timeout": 20.0, "interval": 0.3},
        "enabled_wait": {"timeout": 10.0, "interval": 0.3},
        "disappear_wait": {"timeout": 120.0, "interval": 1.0},
        "staleness_retry": {"timeout": 10.0, "interval": 0.4, "retry_count": 5},
        "exists_wait": {"timeout": 5.0, "interval": 0.3},
        "wait_for_any": {"timeout": 20.0, "interval": 0.4},
        "app_start": {"timeout": 60.0, "interval": 1.0},
        "window_close": {"timeout": 10.0, "interval": 0.5},
        "after_click_pause": 0.2,
        "after_double_click_pause": 0.1,
        "after_right_click_pause": 0.1,
        "combo_open_pause": 0.4,
        "combo_select_pause": 0.4,
        "hotkey_pause": 0.1,
    },
}


def list_presets() -> Dict[str, Dict[str, Any]]:
    return {"default": {}, **PRESET_OVERRIDES}


def build_preset_values(preset: str) -> Dict[str, Any]:
    preset_key = (preset or "default").lower()
    values: Dict[str, Any] = {}
    values.update(deepcopy(TIMEOUT_FIELDS))
    values.update(deepcopy(PAUSE_FIELDS))

    if preset_key == "default":
        return values

    overrides = PRESET_OVERRIDES.get(preset_key)
    if overrides is None:
        raise ValueError(f"Unknown timing preset: {preset}")

    for key, value in overrides.items():

        # 🔹 Eğer action_timeout override edilmişse
        if key == "action_timeout":
            for timeout_key in values.keys():
                if timeout_key.endswith("_action"):
                    base = deepcopy(values[timeout_key])
                    base.update(value)
                    values[timeout_key] = base
            continue

        # 🔹 Normal TIMEOUT_FIELDS override
        if key in TIMEOUT_FIELDS:
            base = deepcopy(values[key])
            base.update(value)
            values[key] = base
        else:
            values[key] = value

    return values
