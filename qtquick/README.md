# UIAuto QtQuick

QtQuick/Windows UIA automation implementation using uiauto-core.

## Overview

`uiauto-qtquick` provides UI automation support for:
- **QtQuick/QML applications** (Qt5/Qt6)
- **WPF applications**
- **Windows UIA-compatible applications**

Key features:
- **element_info.name support**: QtQuick Accessible.name property matching
- **Multi-strategy resolution**: Fallback locator strategies for robustness
- **Recording**: Capture user interactions and generate scenarios (optional)

## Installation

```bash
# Install core + qtquick
pip install ./core ./qtquick

# With recording support
pip install ./core ./qtquick[recording]
```

## Quick Start

### Running Scenarios

```bash
uiauto-qtquick run --elements elements.yaml --scenario scenario.yaml
```

### Inspecting UI

```bash
uiauto-qtquick inspect --window-title-re "Calculator" --out reports
```

### Recording Interactions

```bash
uiauto-qtquick record --elements elements.yaml --scenario-out scenario.yaml
```

## Object Map Example (elements.yaml)

```yaml
app:
  backend: uia
  default_timeout: 10.0

windows:
  main:
    locators:
      - title_re: ".*Calculator.*"

elements:
  button_add:
    window: main
    locators:
      - name: "Plus"
        control_type: "Button"
      - auto_id: "plusButton"
        control_type: "Button"
```

## Scenario Example (scenario.yaml)

```yaml
steps:
  - open_app:
      path: "C:/Program Files/Calculator/Calculator.exe"
  
  - click:
      element: button_add
  
  - type:
      element: input_field
      text: "42"
```

## Documentation

- See [RUNNING.md](../../docs/RUNNING.md) for scenario execution details
- See [INSPECTING.md](../../docs/INSPECTING.md) for UI inspection guide
- See [RECORDING.md](../../docs/RECORDING.md) for recording usage

## License

MIT
