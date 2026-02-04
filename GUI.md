# Desktop GUI Application

`uiauto_ui` provides a user-friendly graphical interface for all `uiauto` CLI commands, built with PySide6 (Qt).

## Features

- **Form-Based Input**: Visual forms for all command arguments
- **File Browsing**: Built-in file/directory selectors with filters
- **Real-Time Output**: Live command output display
- **Status Indicators**: Color-coded status with icons
- **Duration Tracking**: Execution time measurement
- **Copy Output**: One-click output copying
- **Argument Validation**: Pre-run validation with error messages

## Installation

The GUI requires PySide6:

```bash
pip install -e ".[gui]"
```

Or install PySide6 directly:

```bash
pip install PySide6
```

## Usage

### Launch GUI

```bash
python -m uiauto_ui
```

Or from Python:

```python
from uiauto_ui import main
main()
```

### Available Commands

The GUI provides forms for all CLI commands:

| Tab           | Command                | Description                  |
| ------------- | ---------------------- | ---------------------------- |
| Run           | `uiauto run`           | Execute YAML scenarios       |
| Inspect       | `uiauto inspect`       | Analyze UI elements          |
| Record        | `uiauto record`        | Capture user interactions    |
| Validate      | `uiauto validate`      | Validate configuration files |
| List Elements | `uiauto list-elements` | List defined elements        |

## GUI Components

### Run Form

Execute scenarios with full control over:

**Basic Options:**

- Elements file (required): Path to `elements.yaml`
- Scenario file (required): Path to scenario YAML
- App path: Optional application to start
- Report output: Path for JSON report
- Verbose mode: Show detailed step output

**Advanced Options:**

- Schema path: Custom scenario schema
- Variables file: JSON file with variables
- Key-value variables: Manual variable input
- Timeout override: Custom timeout value
- CI mode: CI-optimized settings
- Fast mode: Local development settings

### Inspect Form

Analyze UI elements with options for:

**Basic Options:**

- Window title regex: Filter by window title
- Output directory: Report destination
- Query filter: Control search filter
- Emit elements.yaml: Generate object map

**Advanced Options:**

- Max controls: Limit scan depth
- Include invisible: Show hidden controls
- Exclude disabled: Filter disabled controls
- Window name: Name for generated elements
- State: UI state name
- Merge mode: Merge with existing file

### Record Form

Capture interactions with:

**Basic Options:**

- Elements file (required): Path to update
- Scenario output (required): Where to save recording
- Window title regex: Limit recording scope

**Advanced Options:**

- Window name: Window identifier
- State: UI state for elements
- Debug JSON: Save debug snapshots

### Output Viewer

- Real-time CLI output display
- Color-coded status bar (green=success, red=error)
- Duration display
- Copy to clipboard button
- Clear output button

## Architecture

### Command Specifications (`commands.py`)

The GUI is driven by declarative command specifications:

```python
from uiauto_ui.commands import RUN_COMMAND, ArgSpec, ArgType, Category

# Example argument specification
ArgSpec(
    name="elements",
    short="e",
    arg_type=ArgType.PATH,
    required=True,
    help_text="Path to elements.yaml",
    category=Category.BASIC,
    file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
)
```

### Argument Types

| ArgType          | Widget             | Description                  |
| ---------------- | ------------------ | ---------------------------- |
| `PATH`           | File selector      | Existing file                |
| `SAVE_PATH`      | File selector      | File to save (may not exist) |
| `DIR_PATH`       | Directory selector | Directory path               |
| `STRING`         | Text input         | Free text                    |
| `FLOAT`          | Spin box           | Decimal number               |
| `INT`            | Spin box           | Integer                      |
| `BOOL`           | Checkbox           | Flag/toggle                  |
| `KEY_VALUE_LIST` | Table              | Key=value pairs              |

### Status Mapping (`status_mapping.py`)

Return codes are mapped to visual status:

```python
from uiauto_ui.status_mapping import get_status, StatusLevel

status = get_status("run", return_code=0)
# StatusInfo(level=SUCCESS, message="PASSED", color="#4CAF50", icon="✅")
```

### Executor Threads

- `CLIExecutor`: Runs CLI commands in-process (run, inspect, validate)
- `SubprocessExecutor`: Runs as subprocess for interruptible commands (record)

## Extending the GUI

### Adding a New Command

1. Define specification in `commands.py`:

```python
NEW_COMMAND = CommandSpec(
    name="new-command",
    description="Description of new command",
    args=[
        ArgSpec(name="input", arg_type=ArgType.PATH, required=True, ...),
        ArgSpec(name="output", arg_type=ArgType.SAVE_PATH, ...),
    ]
)

COMMANDS["new-command"] = NEW_COMMAND
```

2. Add status mapping in `status_mapping.py`:

```python
NEW_COMMAND_STATUS_MAP = {
    0: StatusInfo(StatusLevel.SUCCESS, "SUCCESS", "#4CAF50", "✅"),
    1: StatusInfo(StatusLevel.ERROR, "ERROR", "#F44336", "❌"),
}
```

3. Create form class in `app.py` (optional for custom behavior)

### Customizing Forms

Forms are auto-generated from `CommandSpec`, but you can override:

```python
class CustomForm(BaseCommandForm):
    def __init__(self, parent=None):
        super().__init__("custom", parent)

    def _build_ui(self):
        # Custom UI building
        pass

    def validate(self) -> tuple:
        # Custom validation
        return True, ""
```

## Tips

1. **Command Preview**: Forms show the equivalent CLI command
2. **Validation**: Required fields are validated before execution
3. **File Filters**: File dialogs use appropriate filters (YAML, JSON, etc.)
4. **Keyboard Shortcuts**: Standard Qt shortcuts work (Ctrl+C to copy, etc.)
5. **Responsive UI**: Long operations run in background threads

## Limitations

- Windows only (matches core engine requirement)
- Requires PySide6 (Qt6)
- Record command uses subprocess (required for keyboard hooks)
