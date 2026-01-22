# UIAuto QtQuick

QtQuick/WPF UI automation using pywinauto UIA backend with element_info.name support.

## Features

- **Run**: Execute YAML scenarios using object maps
- **Inspect**: Analyze UI elements and generate object maps
- **Record**: Capture user interactions and generate YAML scenarios
- **Name-based Locators**: Support for QtQuick Accessible.name properties

## Installation

```bash
pip install ../core .
# Or with recorder support:
pip install ../core .[recorder]
```

## Usage

### Run Scenario
```bash
uiauto-qtquick run --elements elements.yaml --scenario scenario.yaml
```

### Inspect Window
```bash
uiauto-qtquick inspect --window-title-re "MyApp.*"
uiauto-qtquick inspect --window-title-re "MyApp.*" --emit-elements-yaml elements.yaml
```

### Record Interactions
```bash
uiauto-qtquick record --elements elements.yaml --scenario-out recorded.yaml
```

## Documentation

See `docs/` directory for detailed guides:
- [RUNNING.md](docs/RUNNING.md) - Running scenarios
- [INSPECTING.md](docs/INSPECTING.md) - Inspecting UI elements
- [RECORDING.md](docs/RECORDING.md) - Recording interactions
