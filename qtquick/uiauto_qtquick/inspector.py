# uiauto_qtquick/inspector.py
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from pywinauto import Desktop

from uiauto_core.interfaces import IInspector


# =========================================================
# Helpers
# =========================================================

def _ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _rect_to_list(rect) -> List[int]:
    try:
        return [int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)]
    except Exception:
        return [0, 0, 0, 0]


def _compile_query(query: Optional[str]) -> Optional[re.Pattern]:
    if not query:
        return None
    if query.startswith("regex:"):
        return re.compile(query[len("regex:"):], re.IGNORECASE)
    return re.compile(re.escape(query), re.IGNORECASE)


def _matches_query(info: Dict[str, Any], rx: Optional[re.Pattern]) -> bool:
    if not rx:
        return True
    hay = " | ".join(
        [
            str(info.get("name", "")),
            str(info.get("title", "")),
            str(info.get("auto_id", "")),
            str(info.get("control_type", "")),
            str(info.get("class_name", "")),
            str(info.get("path", "")),
        ]
    )
    return bool(rx.search(hay))


def _normalize_key(s: str) -> str:
    """
    YAML-safe, scenario-friendly element key
    """
    return re.sub(r"[^a-zA-Z0-9_]+", "_", s).strip("_").lower()


# =========================================================
# Locator Candidates (NAME-AWARE)
# =========================================================

def _make_locator_candidates(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Locator önceliği (QtQuick uyumlu):
    1) name (Accessible.name)
    2) auto_id (WPF/WinForms)
    3) title (fallback)
    4) class_name + control_type
    5) control_type only
    """
    ctype = info.get("control_type")
    name = info.get("name")
    auto_id = info.get("auto_id")
    title = info.get("title")
    class_name = info.get("class_name")

    candidates: List[Dict[str, Any]] = []

    # 1) Accessible.name (EN ÖNEMLİ)
    if name and ctype:
        candidates.append({"name": name, "control_type": ctype})
        candidates.append({"name_re": f"(?i){re.escape(name)}", "control_type": ctype})

    # 2) automation_id
    if auto_id and ctype:
        candidates.append({"auto_id": auto_id, "control_type": ctype})

    # 3) title (window_text fallback)
    if title and ctype and title != name:
        candidates.append({"title": title, "control_type": ctype})
        candidates.append({"title_re": f"(?i){re.escape(title)}", "control_type": ctype})

    # 4) class_name
    if class_name and ctype:
        candidates.append({"class_name": class_name, "control_type": ctype})

    # 5) sadece control_type (son çare)
    if ctype:
        candidates.append({"control_type": ctype})

    # duplicate temizle
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for c in candidates:
        k = tuple(sorted(c.items()))
        if k not in seen:
            seen.add(k)
            uniq.append(c)

    return uniq


# =========================================================
# Relative Path (Hierarchy)
# =========================================================

def _parent(ctrl):
    try:
        return ctrl.parent()
    except Exception:
        return None


def _siblings(parent):
    try:
        return parent.children()
    except Exception:
        return []


def build_path(ctrl, max_depth: int = 8) -> str:
    parts: List[str] = []
    cur = ctrl
    depth = 0

    while cur is not None and depth < max_depth:
        ctype = _safe(lambda: cur.element_info.control_type, "Unknown")

        idx = 0
        parent = _parent(cur)
        if parent:
            same = []
            for s in _siblings(parent):
                try:
                    if s.element_info.control_type == ctype:
                        same.append(s)
                except Exception:
                    pass
            try:
                for i, s in enumerate(same):
                    if s.handle == cur.handle:
                        idx = i
                        break
            except Exception:
                pass

        parts.append(f"{ctype}[{idx}]")
        cur = parent
        depth += 1

    return "/".join(reversed(parts))


# =========================================================
# Control Extraction (NAME-AWARE)
# =========================================================

def extract_control_info(ctrl) -> Dict[str, Any]:
    info: Dict[str, Any] = {}

    # UIA core fields
    info["control_type"] = _safe(lambda: ctrl.element_info.control_type, "")
    info["auto_id"] = _safe(lambda: ctrl.element_info.automation_id, "")
    info["class_name"] = _safe(lambda: ctrl.element_info.class_name, "")
    info["process"] = _safe(lambda: ctrl.element_info.process_id, None)

    # ⭐ EN KRİTİK SATIR ⭐
    # QtQuick: Accessible.name -> element_info.name
    info["name"] = _safe(lambda: ctrl.element_info.name, "")

    # window_text SADECE fallback
    info["title"] = info["name"] or _safe(ctrl.window_text, "")

    info["enabled"] = bool(_safe(ctrl.is_enabled, False))
    info["visible"] = bool(_safe(ctrl.is_visible, False))
    info["rect"] = _rect_to_list(_safe(ctrl.rectangle))

    try:
        info["handle"] = int(ctrl.handle)
    except Exception:
        info["handle"] = None

    info["path"] = build_path(ctrl)
    info["locator_candidates"] = _make_locator_candidates(info)

    return info


# =========================================================
# Window Selection (NO WAIT)
# =========================================================

def _select_window(backend: str, title_re: Optional[str]):
    desktop = Desktop(backend=backend)

    try:
        windows = desktop.windows()
    except Exception:
        windows = []

    if not windows:
        raise RuntimeError("Inspector: Desktop üzerinde hiç pencere bulunamadı")

    visible = []
    for w in windows:
        try:
            if w.is_visible():
                visible.append(w)
        except Exception:
            pass

    if not visible:
        raise RuntimeError("Inspector: Görünür pencere bulunamadı")

    if title_re:
        rx = re.compile(title_re)
        for w in visible:
            try:
                if rx.search(w.window_text() or ""):
                    return w
            except Exception:
                pass

    # QtQuick fallback
    return visible[0]


# =========================================================
# Public API
# =========================================================

def inspect_window(
    backend: str = "uia",
    window_title_re: Optional[str] = None,
    max_controls: int = 3000,
    query: Optional[str] = None,
    include_invisible: bool = False,
    include_disabled: bool = True,
) -> Dict[str, Any]:
    """
    Inspector BEKLEMEZ.
    O anda Desktop'ta ne varsa onu dump eder.
    """

    w = _select_window(backend, window_title_re)

    meta = {
        "backend": backend,
        "window_title": _safe(w.window_text, ""),
        "window_handle": _safe(lambda: int(w.handle), None),
        "process": _safe(lambda: w.element_info.process_id, None),
        "title_filter": window_title_re,
    }

    rx = _compile_query(query)
    controls: List[Dict[str, Any]] = []

    try:
        descendants = w.descendants()
    except Exception:
        descendants = []

    for ctrl in descendants[:max_controls]:
        info = extract_control_info(ctrl)

        if not include_invisible and not info["visible"]:
            continue
        if not include_disabled and not info["enabled"]:
            continue
        if not _matches_query(info, rx):
            continue

        controls.append(info)

    # Ranking: name > auto_id > title > visible
    def score(x):
        return (
            1 if x.get("name") else 0,
            1 if x.get("auto_id") else 0,
            1 if x.get("title") else 0,
            1 if x.get("visible") else 0,
        )

    controls.sort(key=score, reverse=True)

    return {
        "meta": meta,
        "controls": controls,
    }


def write_inspect_outputs(result: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    ts = _ts()

    json_path = os.path.join(out_dir, f"inspect_{ts}.json")
    txt_path = os.path.join(out_dir, f"inspect_{ts}.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    lines: List[str] = []
    meta = result["meta"]
    lines.append(f"backend: {meta['backend']}")
    lines.append(f"window_title: {meta['window_title']!r}")
    lines.append(f"process: {meta['process']}")
    lines.append("")
    lines.append(f"controls: {len(result['controls'])}")
    lines.append("-" * 80)

    for i, c in enumerate(result["controls"]):
        lines.append(
            f"[{i}] {c['control_type']} name={c['name']!r} title={c['title']!r} auto_id={c['auto_id']!r} class={c['class_name']!r}"
        )
        lines.append(f"     enabled={c['enabled']} visible={c['visible']} rect={tuple(c['rect'])}")
        lines.append(f"     path={c['path']}")
        for cand in c["locator_candidates"][:3]:
            lines.append(f"       - {cand}")
        lines.append("")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"json": json_path, "txt": txt_path}


# =========================================================
# Stateful YAML Emitter (with merge support)
# =========================================================

def _normalize_locator_for_repo(locator: Dict[str, Any]) -> Dict[str, Any]:
    """
    FIXED FOR QTQUICK: Keep name/name_re as-is (DO NOT convert to title/title_re).
    This preserves the semantic meaning for QtQuick element resolution.
    """
    # Simply return a copy - no transformation needed
    return dict(locator)


def _normalize_existing_elements(elements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes existing YAML locators during merge to ensure
    Repository contract compliance.
    """
    normalized = {}

    for name, spec in elements.items():
        locs = spec.get("locators", [])
        new_locs = []

        for loc in locs:
            new_locs.append(_normalize_locator_for_repo(loc))

        new_spec = dict(spec)
        new_spec["locators"] = new_locs
        normalized[name] = new_spec

    return normalized


def emit_elements_yaml_stateful(
    result: Dict[str, Any],
    out_path: str,
    window_name: str = "main",
    state: str = "default",
    merge: bool = False,
) -> str:
    """
    State-aware YAML emitter with merge support.
    
    FIXED FOR QTQUICK:
      ✔ Preserves name/name_re in locators (no conversion to title/title_re)
      ✔ State-aware merge
      ✔ Stable element keys
      ✔ Multi-locator fallback (top 3)
    """

    import yaml

    if merge and os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}
    else:
        existing = {}

    app_block = existing.get("app", {})
    windows_block = existing.get("windows", {})
    raw_elements = existing.get("elements", {})
    elements_block = _normalize_existing_elements(raw_elements)

    app_block.setdefault("backend", result["meta"]["backend"])

    windows_block.setdefault(
        window_name,
        {
            "locators": [
                {
                    "title_re": result["meta"]["title_filter"]
                    or re.escape(result["meta"]["window_title"] or ".*")
                }
            ]
        },
    )

    for c in result["controls"]:
        cands = c.get("locator_candidates")
        if not cands:
            continue

        base_raw = c.get("name") or c.get("auto_id") or c["control_type"]
        base = _normalize_key(base_raw)

        key = base
        existing_spec = elements_block.get(base)

        if existing_spec:
            existing_state = existing_spec.get("when", {}).get("state")
            if existing_state != state:
                key = f"{base}__{state}"

        # Keep name/name_re as-is (FIXED for QtQuick)
        normalized_locators = [
            _normalize_locator_for_repo(c) for c in cands[:3]
        ]

        spec = {
            "window": window_name,
            "when": {"state": state},
            "locators": normalized_locators,
        }

        elements_block[key] = spec

    final_doc = {
        "app": app_block,
        "windows": windows_block,
        "elements": elements_block,
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(final_doc, f, sort_keys=False, allow_unicode=True)

    return out_path


# =========================================================
# Simple YAML Emitter (backward compatible)
# =========================================================

def emit_elements_yaml(result: Dict[str, Any], out_path: str, window_name: str = "main") -> str:
    import yaml

    elements: Dict[str, Any] = {}
    used = set()
    idx = 0

    for c in result["controls"]:
        cands = c.get("locator_candidates")
        if not cands:
            continue

        name = c.get("name") or c.get("auto_id") or f"{c['control_type'].lower()}_{idx}"
        idx += 1

        base = name
        n = 1
        while name in used:
            name = f"{base}_{n}"
            n += 1
        used.add(name)

        elements[name] = {
            "window": window_name,
            "locators": cands[:3],  # Top 3 candidates for better fallback
        }

    doc = {
        "app": {"backend": result["meta"]["backend"]},
        "windows": {
            window_name: {
                "locators": [{"title_re": result["meta"]["title_filter"] or ".*"}]
            }
        },
        "elements": elements,
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)

    return out_path

# =========================================================
# QtQuickInspector Class (IInspector Implementation)
# =========================================================

class QtQuickInspector(IInspector):
    """
    QtQuick/UIA inspector implementation.
    
    Wraps inspector functions to provide IInspector interface for
    UI tree inspection and object map generation.
    """
    
    def __init__(self, session=None, backend: str = "uia"):
        """
        Initialize QtQuick inspector.
        
        Args:
            session: Optional QtQuickSession (not currently used)
            backend: pywinauto backend ("uia" or "win32")
        """
        self.session = session
        self.backend = backend
    
    def inspect_window(self, **criteria) -> Dict[str, Any]:
        """
        Inspect window and return UI tree structure.
        
        Args:
            **criteria: Window identification criteria
                window_title_re: Optional regex to match window title
                max_controls: Max controls to scan (default: 3000)
                query: Filter controls (string or regex:pattern)
                include_invisible: Include invisible controls
                include_disabled: Include disabled controls
                
        Returns:
            Dictionary with 'meta' and 'controls' keys
        """
        return inspect_window(
            backend=self.backend,
            window_title_re=criteria.get("window_title_re") or criteria.get("title_re"),
            max_controls=criteria.get("max_controls", 3000),
            query=criteria.get("query"),
            include_invisible=criteria.get("include_invisible", False),
            include_disabled=criteria.get("include_disabled", True),
        )
    
    def emit_elements_yaml(self, result: Dict[str, Any], out_path: str, **kwargs) -> str:
        """
        Generate elements.yaml object map from inspection results.
        
        Args:
            result: Inspection result from inspect_window
            out_path: Output file path
            **kwargs: Additional options
                window_name: Window name for object map (default: "main")
                state: State identifier (default: "default")
                merge: Merge with existing YAML (default: False)
                
        Returns:
            Path to generated YAML file
        """
        return emit_elements_yaml_stateful(
            result=result,
            out_path=out_path,
            window_name=kwargs.get("window_name", "main"),
            state=kwargs.get("state", "default"),
            merge=kwargs.get("merge", False),
        )
