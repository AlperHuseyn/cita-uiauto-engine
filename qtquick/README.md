# UIAuto QtQuick

QtQuick/QML UI automation using pywinauto UIA backend for Windows applications.

## Features

- **Run**: Execute YAML scenarios against QtQuick applications
- **Inspect**: Analyze QtQuick UI elements and generate object maps
- **Record**: Capture user interactions and generate test scenarios
- **Element Resolution**: Support for element_info.name matching (QtQuick-specific)
- **Robust Actions**: Fallback strategies for click, type, wait operations

## Installation

```bash
# Install core and qtquick
pip install ../core ./qtquick

# Or in development mode
pip install -e ../core -e ./qtquick

# With recording support
pip install ./qtquick[recorder]
```

## Quick Start

### 1. Inspect Your Application

```bash
uiauto-qtquick inspect --window-title-re "MyApp.*" --emit-elements-yaml elements.yaml
```

This generates an `elements.yaml` object map file.

### 2. Create a Scenario

Create `scenario.yaml`:

```yaml
steps:
  - open_app:
      path: "C:/path/to/myapp.exe"
      wait_for_idle: true
  
  - click:
      element: login_button
  
  - type:
      element: username_field
      text: "testuser"
      clear: true
  
  - click:
      element: submit_button
  
  - assert_text_equals:
      element: status_label
      expected: "Success"
```

### 3. Run the Scenario

```bash
uiauto-qtquick run --elements elements.yaml --scenario scenario.yaml --report report.json
```

## CLI Reference

### Run Command

Execute a test scenario:

```bash
uiauto-qtquick run \
  --elements elements.yaml \
  --scenario scenario.yaml \
  --app "C:/path/to/app.exe" \
  --vars variables.json \
  --report report.json
```

Options:
- `--elements`: Path to elements.yaml (object map) - **required**
- `--scenario`: Path to scenario.yaml - **required**
- `--schema`: Custom scenario schema JSON (optional)
- `--app`: Application path to start (optional, can use open_app step)
- `--vars`: JSON file with variables for substitution
- `--report`: Output path for JSON report (default: report.json)

### Inspect Command

Analyze UI elements:

```bash
uiauto-qtquick inspect \
  --window-title-re "MyApp.*" \
  --out reports \
  --emit-elements-yaml elements.yaml \
  --emit-window-name main \
  --state default
```

Options:
- `--window-title-re`: Filter windows by title regex
- `--out`: Output directory for reports (default: reports)
- `--query`: Filter controls by text/regex
- `--max-controls`: Max descendants to scan (default: 3000)
- `--include-invisible`: Include invisible controls
- `--exclude-disabled`: Exclude disabled controls
- `--emit-elements-yaml`: Generate elements.yaml file
- `--emit-window-name`: Window name in generated YAML (default: main)
- `--state`: UI state name (default: default)
- `--merge`: Merge with existing elements.yaml

### Record Command

Record user interactions:

```bash
uiauto-qtquick record \
  --elements elements.yaml \
  --scenario-out recorded.yaml \
  --window-title-re "MyApp.*" \
  --window-name main \
  --state default
```

Options:
- `--elements`: Path to elements.yaml (will be updated) - **required**
- `--scenario-out`: Output path for recorded scenario - **required**
- `--window-title-re`: Filter recording to specific window
- `--window-name`: Window name for elements (default: main)
- `--state`: UI state name (default: default)
- `--debug-json-out`: Save debug snapshots

## Documentation

See the `docs/` directory for detailed guides:

- [RUNNING.md](docs/RUNNING.md) - Running test scenarios
- [INSPECTING.md](docs/INSPECTING.md) - Inspecting UI elements
- [RECORDING.md](docs/RECORDING.md) - Recording interactions

## QtQuick-Specific Features

### Element Name Matching

QtQuick controls expose `element_info.name` which corresponds to the `Accessible.name` property in QML:

```qml
Button {
    text: "Login"
    Accessible.name: "login_button"
    Accessible.role: Accessible.Button
}
```

In `elements.yaml`:

```yaml
elements:
  login_button:
    window: main
    locators:
      - name: "login_button"
        control_type: "Button"
```

The resolver will match using `element_info.name` for precise element location.

## Configuration

Elements.yaml structure:

```yaml
app:
  backend: "uia"
  default_timeout: 10.0
  polling_interval: 0.2
  artifacts_dir: "artifacts"
  strict_locator_keys: true
  ignore_titlebar_buttons: true

windows:
  main:
    locators:
      - title_re: "MyApp.*"

elements:
  login_button:
    window: main
    locators:
      - name: "login_button"
        control_type: "Button"
      - title: "Login"
        control_type: "Button"
```

## Python API

```python
from uiauto_core import Repository, Runner
from uiauto_qtquick import QtQuickSession, QtQuickResolver, QtQuickActions

# Load object map
repo = Repository("elements.yaml")

# Create QtQuick instances
session = QtQuickSession(backend="uia")
resolver = QtQuickResolver(session, repo)
actions = QtQuickActions(resolver)

# Run scenario
import uiauto_core
import os
schema_path = os.path.join(os.path.dirname(uiauto_core.__file__), "schemas", "scenario.schema.json")
runner = Runner(repo, schema_path=schema_path)

report = runner.run(
    scenario_path="scenario.yaml",
    session=session,
    resolver=resolver,
    actions=actions,
    app_path="C:/path/to/app.exe"
)

print(report["status"])  # "passed" or "failed"
```

## Troubleshooting

### Element Not Found

1. Use `inspect` to verify element properties
2. Try multiple locator strategies (name, title, auto_id)
3. Check if element is in correct window
4. Increase timeout if element loads slowly

### QtQuick-Specific Issues

1. Ensure `Accessible.name` is set in QML
2. Use `--include-invisible` during inspect to see all controls
3. Check `element_info.name` in generated tree dumps

## License

MIT
