# uiauto-engine

A keyword-driven, object-mapped UI automation engine for desktop applications.

Python package: `uiauto`  
CLI: `uiauto run ...`, `uiauto inspect ...`, `uiauto record ...`  
Desktop GUI: `uiauto_ui`

## Features

- **Run**: Execute YAML scenarios using object map (elements.yaml)
- **Inspect**: Analyze UI elements and generate object maps
- **Record**: Capture user interactions and generate semantic YAML scenarios
- **Desktop GUI**: User-friendly graphical interface for all CLI commands

## Installation

### Core Package

```bash
pip install -e .
```

### With GUI Support

```bash
pip install -e ".[gui]"
```

### With Recording Support

```bash
pip install pynput comtypes
```

## Quick Start

### Using CLI

```bash
# Run a scenario
uiauto run --elements object-maps/elements.yaml --scenario scenarios/test.yaml

# Inspect UI elements
uiauto inspect --window-title-re "MyApp.*" --out reports

# Record interactions
uiauto record --elements object-maps/elements.yaml --scenario-out scenarios/recorded.yaml
```

### Using Desktop GUI

```bash
# Launch the GUI application
python -m uiauto_ui
```

Or from Python:

```python
from uiauto_ui import main
main()
```

## Documentation

See [RUNNING.md](RUNNING.md) for details on the run feature.  
See [INSPECTING.md](INSPECTING.md) for details on the inspect feature.  
See [RECORDING.md](RECORDING.md) for details on the recording feature.  
See [GUI.md](GUI.md) for details on the desktop GUI application.

## Project Structure

```
cita-uiauto-engine/
├── uiauto/                 # Core automation engine
│   ├── actions.py          # Keyword action library
│   ├── runner.py           # Scenario runner
│   ├── cli.py              # Command-line interface
│   └── schemas/            # JSON schemas for validation
├── uiauto_ui/              # Desktop GUI application
│   ├── app.py              # Main application window
│   ├── commands.py         # CLI command specifications
│   └── status_mapping.py   # Return code to status mapping
├── object-maps/            # Element definitions (elements.yaml)
├── scenarios/              # Test scenario files
└── reports/                # Output reports and artifacts
```
