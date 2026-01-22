# UIAuto JavaFX

JavaFX UI automation using Java Access Bridge for cross-platform JavaFX applications.

## ⚠️ Alpha Status

This is an alpha implementation. JavaFX automation via Java Access Bridge has limitations:
- Window discovery requires manual integration
- Some operations (hover, right-click) are not fully supported
- Requires Java Runtime Environment with accessibility enabled

## Features

- **Run**: Execute YAML scenarios against JavaFX applications
- **Inspect**: Analyze JavaFX UI elements via Java Accessibility API
- **Element Resolution**: Find elements by accessible name and role
- **Basic Actions**: Click, type, wait, assertions

## Installation

```bash
# Install core and javafx
pip install ../core ./javafx

# Or in development mode
pip install -e ../core -e ./javafx
```

## Requirements

- Java Runtime Environment (JRE) 8 or later
- Java Access Bridge enabled (usually enabled by default on modern Java)
- JPype1 for Python-Java integration

## Quick Start

### 1. Create Elements Map

Create `elements.yaml`:

```yaml
app:
  backend: "javafx"  # Not used but kept for compatibility
  default_timeout: 10.0
  polling_interval: 0.2

windows:
  main:
    locators:
      - title: "My JavaFX App"

elements:
  login_button:
    window: main
    locators:
      - name: "loginButton"  # Matches accessible name in JavaFX
        control_type: "Button"
  
  username_field:
    window: main
    locators:
      - name: "usernameField"
        control_type: "Text"
```

### 2. Create Scenario

Create `scenario.yaml`:

```yaml
steps:
  - open_app:
      path: "/path/to/app.jar"
      wait_for_idle: true
  
  - type:
      element: username_field
      text: "testuser"
      clear: true
  
  - click:
      element: login_button
  
  - assert_text_equals:
      element: status_label
      expected: "Login successful"
```

### 3. Run Scenario

```bash
uiauto-javafx run \
  --elements elements.yaml \
  --scenario scenario.yaml \
  --app /path/to/app.jar \
  --report report.json
```

## CLI Reference

### Run Command

```bash
uiauto-javafx run \
  --elements elements.yaml \
  --scenario scenario.yaml \
  --app app.jar \
  --vars variables.json \
  --report report.json \
  --jvm-path /path/to/libjvm.so \
  --java-args "-Xmx1024m,-Dprop=value" \
  --app-args "arg1,arg2"
```

Options:
- `--elements`: Path to elements.yaml - **required**
- `--scenario`: Path to scenario.yaml - **required**
- `--app`: JavaFX JAR or executable to start
- `--jvm-path`: Custom JVM library path (optional)
- `--java-args`: Comma-separated Java arguments
- `--app-args`: Comma-separated application arguments
- `--vars`: JSON file with variables
- `--report`: Output JSON report path

### Inspect Command

```bash
uiauto-javafx inspect \
  --app app.jar \
  --out reports \
  --max-controls 3000 \
  --include-invisible \
  --wait-seconds 5
```

Options:
- `--app`: JavaFX application to inspect - **required**
- `--out`: Output directory (default: reports)
- `--max-controls`: Max controls to scan (default: 3000)
- `--include-invisible`: Include invisible controls
- `--jvm-path`: Custom JVM library path
- `--java-args`: Comma-separated Java arguments
- `--wait-seconds`: Wait time after app start (default: 5)

## JavaFX Application Setup

For best results, ensure your JavaFX controls have accessible names:

```java
Button loginButton = new Button("Login");
loginButton.setAccessibleText("loginButton");  // Set accessible name

TextField usernameField = new TextField();
usernameField.setAccessibleText("usernameField");
```

Or in FXML:

```xml
<Button text="Login" accessibleText="loginButton" />
<TextField accessibleText="usernameField" />
```

## Python API

```python
from uiauto_core import Repository, Runner
from uiauto_javafx import JavaFXSession, JavaFXResolver, JavaFXActions

# Load object map
repo = Repository("elements.yaml")

# Create JavaFX instances
session = JavaFXSession(jvm_path=None)  # Uses default JVM
resolver = JavaFXResolver(session, repo)
actions = JavaFXActions(resolver)

# Start application
session.start("app.jar", wait_for_idle=True)

# Run scenario
import uiauto_core, os
schema_path = os.path.join(os.path.dirname(uiauto_core.__file__), "schemas", "scenario.schema.json")
runner = Runner(repo, schema_path=schema_path)

report = runner.run(
    scenario_path="scenario.yaml",
    session=session,
    resolver=resolver,
    actions=actions
)

print(report["status"])  # "passed" or "failed"

# Clean up
session.kill()
```

## Limitations

### Current Limitations

1. **Window Discovery**: Limited window enumeration capabilities. You may need to manually set `session.root_context`.

2. **Mouse Operations**: Hover and right-click are not fully implemented. Would require Java Robot class.

3. **Keyboard Operations**: Hotkeys require Java Robot class integration.

4. **Platform Support**: Primarily tested on Windows. Linux/macOS support may vary.

### Workarounds

For advanced operations not supported by JAB, consider:
- Using Java Robot class for mouse/keyboard simulation
- Extending the JABBridge class with native JAB API calls
- Combining with other automation tools

## Troubleshooting

### JVM Not Starting

- Ensure Java is installed: `java -version`
- Check JAVA_HOME environment variable
- Specify custom JVM path: `--jvm-path /path/to/libjvm.so`

### Element Not Found

- Verify accessible names are set in JavaFX application
- Use `inspect` command to see available elements
- Check control_type mappings in resolver

### Access Bridge Issues

- Ensure Java Access Bridge is enabled (usually default)
- Check Java accessibility settings in Control Panel (Windows)

## Examples

See the `examples/` directory for:
- Sample JavaFX application with accessible names
- Example elements.yaml configurations
- Test scenarios

## Development

To extend the JavaFX module:

1. Enhance JABBridge with native JAB API calls for better window discovery
2. Integrate Java Robot class for advanced input simulation
3. Add support for custom JavaFX controls
4. Improve element visibility detection

## License

MIT
