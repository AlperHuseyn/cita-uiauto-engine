# UIAuto JavaFX

JavaFX UI automation using Java Access Bridge for accessibility-based element interaction.

## Features

- **Run**: Execute YAML scenarios using object maps
- **Inspect**: Analyze JavaFX UI elements via Java Accessibility API
- **JAB Bridge**: Python wrapper for Java Access Bridge
- **Accessibility-based**: Uses AccessibleContext for element discovery and interaction

## Installation

```bash
# Requires Java Runtime Environment (JRE)
pip install ../core .
```

## Requirements

- Java Runtime Environment (JRE 8 or later)
- Java Access Bridge enabled (usually enabled by default on Windows)

## Usage

### Run Scenario
```bash
uiauto-javafx run --elements elements.yaml --scenario scenario.yaml --app MyApp.jar
```

### Inspect Window
```bash
uiauto-javafx inspect --window-title "My JavaFX App"
uiauto-javafx inspect --window-title "My App" --emit-elements-yaml elements.yaml
```

## Supported Actions

- **Basic**: click, double_click, type, wait_for, assert_state
- **Text**: assert_text_equals, assert_text_contains
- **Window**: close_window

## Limitations

- **Right-click and hover**: Not supported via Java Accessibility API
- **Hotkeys**: Not supported (requires Robot class or native input)
- **Complex controls**: ComboBox/List selection requires additional implementation
- **Focus**: Limited focus control compared to native UI automation

## Architecture

JavaFX automation uses Java Accessibility API:
1. **JABBridge**: Manages JVM and provides accessibility tree traversal
2. **JavaFXSession**: Application lifecycle management
3. **JavaFXElement**: Element wrapper using AccessibleContext
4. **JavaFXResolver**: Element resolution by name, role, or locator

## Element Locators

Supported locator keys:
- `name`: Accessible name (exact match)
- `name_re`: Accessible name (regex match)
- `control_type`: Element role (Button, Text, ComboBox, etc.)
- `found_index`: Index when multiple matches found

Example:
```yaml
elements:
  submit_button:
    window: main
    locators:
      - name: "Submit"
        control_type: "Button"
```
