# uiauto-engine

Windows-focused UI automation engine for desktop applications, with:

- a Python core package (`uiauto`)
- a CLI (`python -m uiauto.cli`)
- an optional PySide6 desktop GUI (`main_ui.py` or `python -m uiauto_ui.app`)

> This repository currently does **not** include packaging metadata (`pyproject.toml`/`setup.py`), so commands in this documentation use `python -m ...` from the repo root.

## What it does

- Executes YAML scenarios against UI elements defined in `elements.yaml`
- Inspects live UI Automation trees and exports reports / starter object maps
- Records user actions (click/type/hotkey) into semantic scenarios
- Validates object maps and scenarios without executing them
- Lists windows/elements defined in an object map

## Repository structure

```text
cita-uiauto-engine/
├── uiauto/                     # Core engine, CLI, schema, recorder/inspector
├── uiauto_ui/                  # Optional PySide6 desktop UI
├── tests/                      # Unit tests (currently waits utilities)
├── README.md
├── RUNNING.md                  # `run`, `validate`, `list-elements`
├── INSPECTING.md               # `inspect`
├── RECORDING.md                # `record`
└── GUI.md                      # Desktop GUI usage
```

## Requirements

- **OS:** Windows (UI automation/runtime features rely on UIA/Win32)
- **Python:** 3.8+
- **Core dependencies used by code:** `pywinauto`, `PyYAML`, `jsonschema`, `Pillow`
- **Recorder optional dependencies:** `pynput`, `comtypes`
- **GUI dependencies:** `PySide6`, `qt-material`
- **Optional GUI theming:** `pyqtdarktheme`

## Installation (repo-local)

Install runtime dependencies manually:

```bash
pip install pywinauto pyyaml jsonschema pillow
```

Optional recorder extras:

```bash
pip install pynput comtypes
```

Optional GUI extras:

```bash
pip install -r requirements-ui.txt
# optional theme support
pip install pyqtdarktheme
```

## CLI quick start

```bash
# Run one scenario
python -m uiauto.cli run `
  --elements object-maps/elements.yaml `
  --scenario scenarios/test.yaml

# Inspect desktop UI and write JSON/TXT reports
python -m uiauto.cli inspect --out reports

# Record interactions (Ctrl+Alt+Q to stop)
python -m uiauto.cli record `
  --elements object-maps/elements.yaml `
  --scenario-out scenarios/recorded.yaml

# Validate files without execution
python -m uiauto.cli validate `
  --elements object-maps/elements.yaml `
  --scenario scenarios/test.yaml

# List windows and elements in object map
python -m uiauto.cli list-elements --elements object-maps/elements.yaml
```

## GUI quick start

```bash
python main_ui.py
# or
python -m uiauto_ui.app
```

## Documentation map

- [RUNNING.md](RUNNING.md) — run/validate/list-elements usage, keywords, exit codes
- [INSPECTING.md](INSPECTING.md) — inspector output and YAML emission
- [RECORDING.md](RECORDING.md) — recorder behavior and limitations
- [GUI.md](GUI.md) — PySide6 desktop interface

## Notes on current implementation

- `run` supports single scenario (`--scenario`) and bulk execution (`--scenarios-dir`).
- Timing presets are available via `--fast`, `--slow`, `--ci` and `--default`.
