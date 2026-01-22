# Inspecting UI (`uiauto inspect`)

`uiauto inspect` scans visible desktop windows (UIA) and dumps control information to help you build or troubleshoot `elements.yaml`.

Useful for:

- Discovering `name` (QtQuick `Accessible.name`)
- Identifying `control_type`, `class_name`, `auto_id`
- Generating candidate locators
- Emitting starter `elements.yaml` with optional merging

## Basic Usage

```bash
python -m uiauto.cli inspect --out reports
```

Output:

- `reports/inspect_<timestamp>.json`
- `reports/inspect_<timestamp>.txt`

## Target Specific Window

Use regex on window title:

```bash
python -m uiauto.cli inspect `
  --window-title-re "QtQuickTaskApp.*" `
  --out reports
```

Selection behavior:

- Lists visible windows
- If `--window-title-re` matches, picks first match
- Otherwise uses first visible window

## Filter Controls

`--query` filters by case-insensitive substring across: name, title, auto_id, control_type, class_name, path.

```bash
python -m uiauto.cli inspect --query "login" --out reports
```

Regex search:

```bash
python -m uiauto.cli inspect --query "regex: (? i)button" --out reports
```

## Performance Options

```bash
python -m uiauto.cli inspect --max-controls 3000
python -m uiauto.cli inspect --include-invisible
python -m uiauto.cli inspect --exclude-disabled
```

## Generate `elements.yaml`

Emit object map from inspect output:

```bash
python -m uiauto.cli inspect `
  --window-title-re "QtQuickTaskApp.*" `
  --out reports
  --emit-elements-yaml object-maps/generated.yaml
```

### Configure Window Name and State

```bash
python -m uiauto.cli inspect `
  --emit-elements-yaml object-maps/elements.yaml `
  --emit-window-name main `
  --state default
```

### Merge into Existing File

```bash
python -m uiauto.cli inspect `
  --emit-elements-yaml object-maps/elements.yaml `
  --merge
```

Merge behavior:

- Preserves existing content
- Normalizes existing locators (QtQuick-safe: keeps `name`/`name_re`)
- Adds new elements with stable keys from `name` or `auto_id`
- Creates suffixed keys for same element in different states

## Locator Priority

Inspector generates candidates with this preference:

1. `name`/`name_re` + `control_type` (best for QtQuick)
2. `auto_id` + `control_type`
3. `title`/`title_re` + `control_type`
4. `class_name` + `control_type`
5. `control_type` only (last resort)

**Recommendation**: Keep first 2-3 candidates for resilience.

## Example Workflow

### 1. Inspect Application

```bash
python -m uiauto.cli inspect `
  --window-title-re "MyApp" `
  --out reports `
  --emit-elements-yaml object-maps/elements.yaml
```

### 2. Review Generated Elements

```bash
type object-maps/elements.yaml
```

### 3. Test in Scenario

```yaml
steps:
  - click:
      element: loginbutton
```

### 4. Run Scenario

```bash
python -m uiauto.cli run `
  --elements object-maps/elements.yaml `
  --scenario scenarios/test.yaml
```

### 5. Refine Locators

If element not found:

- Re-inspect with `--query "login"`
- Add fallback locators
- Verify control_type matches
