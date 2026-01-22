# DEPRECATED

This documentation has been moved to `qtquick/docs/RECORDING.md`

See the new monorepo structure in README.md

---

# Recording User Interactions

The `uiauto record` command captures user interactions with a Windows application and generates semantic YAML scenarios compatible with `uiauto run`.

## Features

- **Semantic Recording**: Converts clicks, typing, and hotkeys into high-level steps
- **No Coordinates**: Maps actions to elements using UIA locators
- **QtQuick Compatible**: Prefers `name`/`name_re` locators based on `Accessible.name`
- **Keystroke Grouping**: Consecutive typing merged into single `type` steps
- **Incremental Updates**: Automatically updates `elements.yaml` with new elements
- **Safe Merging**: Preserves existing element definitions

## Installation

Recorder requires optional dependencies:

```bash
pip install pynput comtypes
```

## Basic Usage

```bash
python -m uiauto.cli record `
  --elements object-maps/elements.yaml `
  --scenario-out scenarios/recorded.yaml `
  --window-title-re "MyApp.*"
```

This will:

1. Start recording interactions with windows matching "MyApp.\*"
2. Capture clicks and typing
3. Save scenario to `scenarios/recorded.yaml` on stop
4. Update `object-maps/elements.yaml` with new elements

## Full Options

```bash
python -m uiauto.cli record `
  --elements <path>              # Path to elements.yaml (required)
  --scenario-out <path>          # Output scenario YAML (required)
  --window-title-re <regex>      # Filter to specific window (optional)
  --window-name <name>           # Window name in elements.yaml (default: "main")
  --state <state>                # UI state for recorded elements (default: "default")
  --debug-json-out <path>        # Save debug snapshots (optional)
```

## Recording Workflow

### 1. Start Recorder

```bash
python -m uiauto.cli record `
  --elements object-maps/elements.yaml `
  --scenario-out scenarios/recorded. yaml
```

### 2. Interact with Application

- **Click** buttons, fields, items → Generates `click` steps
- **Type** into text fields → Generates `type` steps
- **Hotkeys** (Ctrl+S, etc.) → Generates `hotkey` steps

### 3. Stop Recording

- Press `Ctrl+Alt+Q` (works globally, no terminal focus needed)
- Or press `Ctrl+C` in terminal

### 4. Review Outputs

- `scenarios/recorded.yaml`: Generated scenario
- `object-maps/elements.yaml`: Updated with new elements

## Generated Steps

### Click

```yaml
- click:
    element: loginbutton
```

### Type

```yaml
- type:
    element: usernamefield
    text: "AutomationTest"
```

### Hotkey

```yaml
- hotkey:
    keys: "^l"
```

## Supported Interactions

Currently recorded:

- Single clicks (`click`)
- Text typing (`type`)
- Keyboard shortcuts (`hotkey`)

**Not yet recorded** (add manually):

- `double_click`
- `right_click`
- `hover`
- `set_checkbox`
- `select_combobox`
- `select_list_item`
- `wait` steps
- Assertions

## Element Locator Strategy

Recorder generates locators with this priority:

1. `name` + `control_type` (best for QtQuick)
2. `auto_id` + `control_type`
3. `title` + `control_type`
4. `class_name` + `control_type`

Example generated element:

```yaml
loginbutton:
  window: main
  when:
    state: default
  locators:
    - name: loginButton
      control_type: Button
    - name_re: (?i)loginButton
      control_type: Button
    - class_name: Button_QMLTYPE_4
      control_type: Button
```

## State Management

Record elements for different UI states:

```bash
# Login screen
uiauto record \
  --elements object-maps/elements. yaml \
  --scenario-out scenarios/login.yaml \
  --state login

# Main screen
uiauto record \
  --elements object-maps/elements. yaml \
  --scenario-out scenarios/main.yaml \
  --state main
```

Elements with same name in different states get suffixed:

- `taskinput` (state: default)
- `taskinput__login` (state: login)

## Enhancing Recorded Scenarios

### Add Waits

Insert explicit wait steps for async UI:

```yaml
steps:
  - click:
      element: loginbutton

  # Add wait
  - wait:
      element: dashboard
      state: visible
      timeout: 10

  - type:
      element: searchfield
      text: "query"
```

### Add Assertions

Validate UI state:

```yaml
steps:
  - click:
      element: submitbutton

  # Add assertion
  - assert_text_contains:
      element: statuslabel
      substring: "Success"
```

### Add Variables

Replace hardcoded values:

```yaml
vars:
  username: TestUser

steps:
  - type:
      element: usernamefield
      text: ${username}
```

### Add Control-Specific Operations

Replace generic clicks with semantic operations:

```yaml
# Replace:
- click:
    element: acceptterms

# With:
- set_checkbox:
    element: acceptterms
    checked: true
```

## Limitations

- **Windows Only**: Requires Windows with UIA
- **Focus-Based**: Only captures elements receiving keyboard focus
- **Best-Effort**: May miss transient UI elements
- **Actions Only**: No assertions or waits generated
- **Subset of Keywords**: Only click/type/hotkey supported

## Tips

1. **Window Filtering**: Use `--window-title-re` to avoid capturing other apps
2. **Slow Actions**: Perform actions deliberately with pauses
3. **Stop Hotkey**: Use `Ctrl+Alt+Q` (works without terminal focus)
4. **Review Output**: Always review and enhance recorded scenarios
5. **Add Waits**: Insert waits for async operations
6. **Test Playback**: Run recorded scenario to verify correctness

## Debugging

Enable debug mode:

```bash
uiauto record \
  --elements object-maps/elements.yaml \
  --scenario-out scenarios/recorded.yaml \
  --debug-json-out debug_snapshots.json
```

This creates a JSON file with detailed element information for troubleshooting.

## Example Session

```bash
$ uiauto record --elements object-maps/elements.yaml --scenario-out scenarios/test.yaml

🎬 Recording started.  Press Ctrl+Alt+Q to stop.

  🖱️  Click: loginbutton
  ⌨️  Type: usernamefield = 'TestUser'
  🖱️  Click: submitbutton
  ⌨️  Hotkey: ^s

🛑 Stopped. Captured 4 steps.
📝 Scenario:  scenarios/test.yaml
🗺️  Elements: object-maps/elements.yaml (3 elements added)
```
