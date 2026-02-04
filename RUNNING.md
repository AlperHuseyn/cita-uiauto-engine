# Running Scenarios (`uiauto run`)

`uiauto run` executes a YAML scenario (steps) using an object map (`elements.yaml`).

## Requirements

- Windows with UIA support
- Python 3.7+ with dependencies: `pywinauto`, `pyyaml`, `jsonschema`, `pillow`

## Inputs

### 1) Object Map: `elements.yaml`

Describes:

- **app**: defaults (backend, timeouts, artifacts directory)
- **windows**: locators for top-level windows
- **elements**: locators for UI controls

Example:

```yaml
app:
  backend: uia
  default_timeout: 10
  polling_interval: 0.2
  artifacts_dir: artifacts

windows:
  main:
    locators:
      - title_re: "QtQuickTaskApp"

elements:
  loginbutton:
    window: main
    when:
      state: default
    locators:
      - name: loginButton
        control_type: Button
      - class_name: Button_QMLTYPE_7
        control_type: Button
```

**QtQuick Support**: The framework supports `name`/`name_re` locators mapped to `element_info.name` (QtQuick `Accessible.name`).

**Locator Resilience**: Provide multiple fallback locators for robustness.

### 2) Scenario: `scenario.yaml`

Structure:

- `vars` (optional): variable definitions
- `steps` (required): ordered list of actions

**Variable Substitution**: Use `${varName}` in strings.

Example:

```yaml
vars:
  username: TestUser
  country: Turkey

steps:
  - open_app:
      path: "C:\\path\\to\\App.exe"

  - wait:
      element: loginbutton
      state: visible

  - type:
      element: usernamefield
      text: ${username}

  - click:
      element: loginbutton

  - set_checkbox:
      element: acceptterms
      checked: true

  - select_combobox:
      element: countryselect
      option: ${country}
```

## Basic Usage

```bash
python -m uiauto.cli run `
  --elements object-maps/elements.yaml `
  --scenario scenarios/scenario.yaml `
  --report report.json
```

### Exit Codes

- `0`: Scenario passed
- `1`: Configuration error
- `2`: Scenario failed

### Output

- JSON report printed to stdout
- JSON report written to file (default: `report.json`)

## Runtime Variables

Supply external variables via JSON file:

```bash
python -m uiauto.cli run `
  --elements object-maps/elements.yaml `
  --scenario scenarios/scenario.yaml `
  --vars vars.json
```

`vars.json`:

```json
{
  "username": "RuntimeUser",
  "task": "Dynamic Task"
}
```

**Merge Behavior**: CLI variables override scenario variables.

## Starting the Application

### Method 1: `open_app` step (recommended)

```yaml
steps:
  - open_app:
      path: "C:\\path\\App.exe"
      wait_for_idle: false
```

### Method 2: `--app` CLI argument

```bash
python -m uiauto.cli run `
  --elements object-maps/elements.yaml `
  --scenario scenarios/scenario.yaml `
  --app "C:\\path\\App.exe"
```

## Available Keywords

### Basic Interactions

#### `click`

Single click on element.

```yaml
- click:
    element: loginbutton
```

Optional overrides:

```yaml
- click:
    element: loginbutton
    overrides:
      title_re: "(?i)login"
```

#### `double_click`

Double-click on element.

```yaml
- double_click:
    element: fileitem
```

#### `right_click`

Right-click on element (opens context menu).

```yaml
- right_click:
    element: fileitem
```

#### `hover`

Move mouse over element (triggers hover menus/tooltips).

```yaml
- hover:
    element: helpicon
```

#### `type`

Type text into element.

```yaml
- type:
    element: usernamefield
    text: "MyUsername"
    clear: true
```

Parameters:

- `text` (required): text to type
- `clear` (optional, default: true): clear existing text first

#### `click_and_type`

Click an element and type text in one step. Useful for fields that need focus before typing.

```yaml
- click_and_type:
    element: searchfield
    text: "search query"
    clear: true
```

Parameters:

- `element` (required): element to click and type into
- `text` (required): text to type
- `clear` (optional, default: true): clear existing text first

#### `hotkey`

Send global keyboard combination.

```yaml
- hotkey:
    keys: "^s"
```

Common keys:

- `^` = Ctrl
- `%` = Alt
- `+` = Shift
- `{ENTER}`, `{TAB}`, `{ESC}`, etc.

Examples:

- `^s` = Ctrl+S
- `^+s` = Ctrl+Shift+S
- `%{F4}` = Alt+F4

### Wait and Synchronization

#### `wait`

Wait for element to reach state.

```yaml
- wait:
    element: loginbutton
    state: visible
    timeout: 15
```

States:

- `exists`: element exists in UI tree
- `visible`: element is visible on screen
- `enabled`: element is visible and enabled

#### `wait_for_gone`

Wait for an element to disappear from the UI.

```yaml
- wait_for_gone:
    element: loadingspinner
    timeout: 30
```

Parameters:

- `element` (required): element to wait for disappearance
- `timeout` (optional): max wait time in seconds

Useful for:

- Waiting for loading indicators to disappear
- Waiting for dialogs to close
- Waiting for transitions to complete

#### `wait_for_any`

Wait for any one of multiple elements to appear. Returns when the first element is found.

```yaml
- wait_for_any:
    elements:
      - successmessage
      - errormessage
      - timeoutdialog
    timeout: 30
```

Parameters:

- `elements` (required): list of element names to wait for
- `timeout` (optional): max wait time in seconds

Useful for:

- Handling multiple possible outcomes
- Detecting success or failure states
- Waiting for any of several dialogs

### Conditional Actions

#### `click_if_exists`

Click an element if it exists, otherwise continue without error.

```yaml
- click_if_exists:
    element: cookiebanner_accept
    timeout: 2
```

Parameters:

- `element` (required): element to click if present
- `timeout` (optional, default: 2): how long to wait for element

Useful for:

- Dismissing optional dialogs (cookie banners, tips, etc.)
- Handling conditional UI elements
- Non-blocking optional interactions

### Text Operations

#### `get_text`

Get text content of an element. Optionally store in a variable.

```yaml
- get_text:
    element: statuslabel
    store_as: current_status
```

Parameters:

- `element` (required): element to get text from
- `store_as` (optional): variable name to store the text

The stored variable can be used in subsequent steps:

```yaml
- get_text:
    element: totalprice
    store_as: price

- assert_text_contains:
    element: confirmationdialog
    substring: ${price}
```

### Control-Specific Operations

#### `set_checkbox`

Set checkbox to specific state (idempotent).

```yaml
- set_checkbox:
    element: acceptterms
    checked: true
```

**Robustness**: Tries UIA TogglePattern, Win32 check/uncheck, and click fallback.

#### `select_combobox`

Select option in combobox/dropdown.

```yaml
- select_combobox:
    element: countryselect
    option: "United States"
```

Select by index:

```yaml
- select_combobox:
    element: countryselect
    option: "2"
    by_index: true
```

For QtQuick ComboBoxes, use `item_element`:

```yaml
- select_combobox:
    element: prioritycombo
    option: "High"
    item_element: priority_high_item
```

**Robustness**: Tries direct select, expand+click item, and type+enter.

#### `select_combobox_item`

Select an item in a QtQuick ComboBox by clicking the combobox, then clicking the list item. Designed specifically for QtQuick where standard selection patterns don't work.

```yaml
- select_combobox_item:
    combobox: prioritycombo
    item: priority_high_item
```

Parameters:

- `combobox` (required): ComboBox element name
- `item` (required): ListItem element name to select

This is the recommended approach for QtQuick ComboBoxes.

#### `select_list_item`

Select item in list/listview.

By text:

```yaml
- select_list_item:
    element: tasklist
    item_text: "Complete project"
```

By index:

```yaml
- select_list_item:
    element: tasklist
    item_index: 2
```

### Assertions

#### `assert`

Assert element state.

```yaml
- assert:
    element: loginbutton
    state: enabled
```

#### `assert_text_equals`

Assert element text equals expected value.

```yaml
- assert_text_equals:
    element: statuslabel
    expected: "Login successful"
```

#### `assert_text_contains`

Assert element text contains substring.

```yaml
- assert_text_contains:
    element: statuslabel
    substring: "Success"
```

#### `assert_checkbox_state`

Assert checkbox state.

```yaml
- assert_checkbox_state:
    element: acceptterms
    checked: true
```

#### `assert_count`

Assert item count in list/combobox.

```yaml
- assert_count:
    element: tasklist
    expected: 5
```

### Window and Application Management

#### `open_app`

Start application.

```yaml
- open_app:
    path: "C:\\path\\App.exe"
    wait_for_idle: false
```

#### `connect`

Connect to existing application.

```yaml
- connect:
    process: 1234
```

#### `close_window`

Close window by name.

```yaml
- close_window:
    window: dialog
```

#### `kill_app`

Force terminate application.

```yaml
- kill_app: {}
```

## Keyword Reference Summary

| Category        | Keyword                 | Description                       |
| --------------- | ----------------------- | --------------------------------- |
| **Clicks**      | `click`                 | Single click                      |
|                 | `double_click`          | Double click                      |
|                 | `right_click`           | Right click (context menu)        |
|                 | `hover`                 | Mouse hover                       |
|                 | `click_if_exists`       | Click if element exists           |
| **Text**        | `type`                  | Type text into element            |
|                 | `click_and_type`        | Click then type (one step)        |
|                 | `get_text`              | Get element text                  |
| **Waits**       | `wait`                  | Wait for element state            |
|                 | `wait_for_gone`         | Wait for element to disappear     |
|                 | `wait_for_any`          | Wait for any of multiple elements |
| **Checkboxes**  | `set_checkbox`          | Set checkbox state                |
|                 | `assert_checkbox_state` | Assert checkbox state             |
| **ComboBoxes**  | `select_combobox`       | Select combobox option            |
|                 | `select_combobox_item`  | QtQuick combobox selection        |
| **Lists**       | `select_list_item`      | Select list item                  |
|                 | `assert_count`          | Assert item count                 |
| **Assertions**  | `assert`                | Assert element state              |
|                 | `assert_text_equals`    | Assert text equals                |
|                 | `assert_text_contains`  | Assert text contains              |
| **Hotkeys**     | `hotkey`                | Send keyboard shortcut            |
| **App Control** | `open_app`              | Start application                 |
|                 | `connect`               | Connect to running app            |
|                 | `close_window`          | Close window                      |
|                 | `kill_app`              | Force terminate                   |

## Complete Example

```yaml
vars:
  username: TestUser
  password: SecurePass123
  country: Turkey

steps:
  - open_app:
      path: "C:\\MyApp\\App.exe"

  - wait:
      element: loginbutton
      state: visible
      timeout: 15

  # Dismiss optional cookie banner
  - click_if_exists:
      element: cookiebanner_close
      timeout: 2

  - type:
      element: usernamefield
      text: ${username}

  - type:
      element: passwordfield
      text: ${password}

  - click:
      element: loginbutton

  # Wait for loading to complete
  - wait_for_gone:
      element: loadingspinner
      timeout: 30

  # Handle success or error
  - wait_for_any:
      elements:
        - dashboard
        - errordialog
      timeout: 15

  - wait:
      element: dashboard
      state: visible

  - assert_text_contains:
      element: welcomelabel
      substring: "Welcome"

  # Get current balance for later verification
  - get_text:
      element: balancelabel
      store_as: initial_balance

  - set_checkbox:
      element: rememberme
      checked: true

  # QtQuick ComboBox selection
  - select_combobox_item:
      combobox: countrycombo
      item: country_turkey_item

  - double_click:
      element: settingsicon

  - assert_count:
      element: settingslist
      expected: 8

  - hotkey:
      keys: "^s"

  - close_window:
      window: settings

  - kill_app: {}
```

## Debugging Failures

### Artifacts

When resolution fails, the engine generates artifacts:

- Screenshot: `artifacts/<prefix>_screenshot_<timestamp>.png`
- Control tree: `artifacts/<prefix>_tree_<timestamp>.txt`

Configure artifacts directory in `elements.yaml`:

```yaml
app:
  artifacts_dir: artifacts
```

### Common Issues

**Element not found**:

1. Run `uiauto inspect --window-title-re "YourApp.*"` to verify locators
2. Add multiple fallback locators (name → auto_id → class_name)
3. Check control_type matches

**Timing issues**:

1. Add explicit `wait` steps before interactions
2. Use `wait_for_gone` for loading indicators
3. Increase `default_timeout` in elements.yaml
4. Use `wait_for_idle: true` in `open_app`

**QtQuick apps**:

1. Prefer `name`/`name_re` locators (maps to `Accessible.name`)
2. Avoid `auto_id` (often empty in QtQuick)
3. Use `select_combobox_item` for ComboBox selection
4. Use inspector to verify `element_info.name` values

**Conditional UI**:

1. Use `click_if_exists` for optional dialogs
2. Use `wait_for_any` for multiple possible outcomes
3. Use `wait_for_gone` for disappearing elements

### Validation

Schema validation errors indicate malformed scenario:

```
Scenario schema validation failed:
- ['steps', 0, 'click']: 'element' is a required property
```

Fix: Ensure all required properties are present and correctly spelled.

## Advanced: Locator Overrides

Override locators at runtime for dynamic UIs:

```yaml
- click:
    element: dynamicbutton
    overrides:
      name_re: "Submit.*"
      control_type: Button
```

This temporarily replaces the element's locators for this step only.
