# UIAuto Engine - Monorepo

Multi-framework desktop UI automation toolkit with YAML-based scenario execution.

## Packages

This monorepo contains three packages:

### 📦 **core/** - Framework-agnostic engine
Framework-independent automation core providing:
- YAML object map repository
- Scenario runner with variable substitution
- Wait utilities and polling
- Rich exception types with artifacts
- Abstract interfaces for implementations

### 🖥️ **qtquick/** - QtQuick/WPF automation
QtQuick and WPF automation using pywinauto UIA backend:
- Element resolution via `element_info.name` (QtQuick Accessible.name)
- Run, inspect, and record UI interactions
- Windows desktop automation
- Full pywinauto feature set

### ☕ **javafx/** - JavaFX automation
JavaFX automation using Java Access Bridge:
- Accessibility-based element discovery
- Run and inspect JavaFX applications
- Cross-platform Java UI automation
- JAB API wrapper

## Installation

### QtQuick Only
```bash
pip install ./core ./qtquick
# Or with recorder support:
pip install ./core ./qtquick[recorder]
```

### JavaFX Only
```bash
pip install ./core ./javafx
```

### Both Frameworks
```bash
pip install ./core ./qtquick ./javafx
```

### Development Mode
```bash
pip install -e ./core -e ./qtquick -e ./javafx
```

## Usage

### QtQuick
```bash
# Run scenario
uiauto-qtquick run --elements elements.yaml --scenario scenario.yaml

# Inspect window
uiauto-qtquick inspect --window-title-re "MyApp.*"

# Record interactions
uiauto-qtquick record --elements elements.yaml --scenario-out recorded.yaml
```

### JavaFX
```bash
# Run scenario
uiauto-javafx run --elements elements.yaml --scenario scenario.yaml --app MyApp.jar

# Inspect window
uiauto-javafx inspect --window-title "My JavaFX App"
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      uiauto-core                        │
│  (Repository, Runner, Waits, Exceptions, Interfaces)   │
└─────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
┌─────────▼──────────┐          ┌──────────▼─────────┐
│   uiauto-qtquick   │          │   uiauto-javafx    │
│                    │          │                    │
│ • QtQuickSession   │          │ • JavaFXSession    │
│ • QtQuickResolver  │          │ • JavaFXResolver   │
│ • QtQuickElement   │          │ • JavaFXElement    │
│ • QtQuickActions   │          │ • JavaFXActions    │
│                    │          │ • JABBridge        │
└────────────────────┘          └────────────────────┘
```

## Object Map Format

All implementations use the same YAML object map format:

```yaml
app:
  backend: uia  # or jab for JavaFX
  default_timeout: 10.0
  polling_interval: 0.2

windows:
  main:
    locators:
      - title_re: "MyApp.*"

elements:
  username_field:
    window: main
    locators:
      - name: "Username"  # QtQuick: Accessible.name / JavaFX: AccessibleName
        control_type: "Edit"
  
  login_button:
    window: main
    locators:
      - name: "Login"
        control_type: "Button"
```

## Scenario Format

```yaml
vars:
  username: "testuser"
  password: "secret123"

steps:
  - open_app:
      path: "C:\\MyApp\\app.exe"
  
  - type:
      element: username_field
      text: "${username}"
  
  - type:
      element: password_field
      text: "${password}"
  
  - click:
      element: login_button
  
  - assert_text_contains:
      element: welcome_message
      substring: "Welcome"
```

## Documentation

- **core/README.md** - Core package documentation
- **qtquick/README.md** - QtQuick package documentation
- **qtquick/docs/** - Detailed guides (RUNNING.md, INSPECTING.md, RECORDING.md)
- **javafx/README.md** - JavaFX package documentation

## Examples

Example object maps and scenarios are provided in:
- `object-maps/` - Sample object maps
- `scenarios/` - Sample scenarios

## Development

### Running Tests
```bash
# Core tests
cd core && python -m pytest tests/

# QtQuick tests (requires Windows with UIA support)
cd qtquick && python -m pytest tests/

# JavaFX tests (requires JRE)
cd javafx && python -m pytest tests/
```

### Contributing

Contributions are welcome! This monorepo structure makes it easy to:
- Fix bugs in core that benefit all implementations
- Add new framework implementations
- Improve existing implementations independently

## License

MIT License

## Requirements

### QtQuick Package
- Windows OS
- Python 3.8+
- pywinauto >= 0.6.8
- comtypes >= 1.1.7

### JavaFX Package
- Python 3.8+
- Java Runtime Environment (JRE 8+)
- JPype1 >= 1.4.0

## Backwards Compatibility

The original `uiauto` package has been split into this monorepo. To migrate:

```python
# OLD:
from uiauto import Repository, Session, Resolver, Actions, Runner

# NEW:
from uiauto_core import Repository, Runner
from uiauto_qtquick import QtQuickSession, QtQuickResolver, QtQuickActions
```

## Support

For issues, questions, or contributions, please visit:
https://github.com/AlperHuseyn/cita-uiauto-engine
