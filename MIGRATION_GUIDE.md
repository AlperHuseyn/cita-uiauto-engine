# Migration Guide: uiauto → Monorepo

## Overview

The `uiauto` package has been refactored into a modular monorepo with three packages:

1. **uiauto-core** - Framework-agnostic automation engine
2. **uiauto-qtquick** - QtQuick/WPF automation (replaces original uiauto)
3. **uiauto-javafx** - JavaFX automation (new)

## Why This Change?

- **Separation of Concerns**: Core logic is now independent of UI frameworks
- **Independent Dependencies**: Install only what you need
- **Maintainability**: Bug fixes in core benefit all implementations
- **Extensibility**: Easy to add new frameworks (Electron, Avalonia, etc.)

## Installation

### Before
```bash
# Old approach (if there was a package)
pip install uiauto
```

### After
```bash
# QtQuick users
pip install ./core ./qtquick

# JavaFX users  
pip install ./core ./javafx

# Both
pip install ./core ./qtquick ./javafx
```

## Code Migration

### Import Changes

```python
# OLD imports
from uiauto import Repository, Session, Resolver, Actions, Runner

# NEW imports
from uiauto_core import Repository, Runner
from uiauto_qtquick import QtQuickSession, QtQuickResolver, QtQuickActions
```

### Runner Usage

```python
# OLD
repo = Repository("elements.yaml")
runner = Runner(repo, schema_path="scenario.schema.json")
runner.run(scenario_path="scenario.yaml", app_path="app.exe")

# NEW
from uiauto_core import Repository, Runner
from uiauto_qtquick import QtQuickSession, QtQuickResolver, QtQuickActions

repo = Repository("elements.yaml")
runner = Runner(repo, schema_path="scenario.schema.json")

# Create factory functions
def session_factory():
    return QtQuickSession(
        backend=repo.app.backend,
        default_timeout=repo.app.default_timeout,
        polling_interval=repo.app.polling_interval,
    )

def resolver_factory(sess, repo):
    return QtQuickResolver(sess, repo)

def actions_factory(resolver):
    return QtQuickActions(resolver)

# Run with factories
runner.run(
    scenario_path="scenario.yaml",
    session_factory=session_factory,
    resolver_factory=resolver_factory,
    actions_factory=actions_factory,
    app_path="app.exe",
)
```

### Direct Usage (Without Runner)

```python
# OLD
from uiauto import Repository, Session, Resolver, Actions

repo = Repository("elements.yaml")
session = Session()
session.start("app.exe")
resolver = Resolver(session, repo)
actions = Actions(resolver)
actions.click("my_button")

# NEW
from uiauto_core import Repository
from uiauto_qtquick import QtQuickSession, QtQuickResolver, QtQuickActions

repo = Repository("elements.yaml")
session = QtQuickSession()
session.start("app.exe")
resolver = QtQuickResolver(session, repo)
actions = QtQuickActions(resolver)
actions.click("my_button")
```

## CLI Changes

### Before
```bash
python -m uiauto.cli run --elements elements.yaml --scenario scenario.yaml
```

### After
```bash
# QtQuick
uiauto-qtquick run --elements elements.yaml --scenario scenario.yaml

# JavaFX
uiauto-javafx run --elements elements.yaml --scenario scenario.yaml
```

## Object Map Changes

No changes required! The YAML format is the same:

```yaml
app:
  backend: uia  # or jab for JavaFX
  default_timeout: 10.0

windows:
  main:
    locators:
      - title_re: "MyApp.*"

elements:
  my_button:
    window: main
    locators:
      - name: "Click Me"
        control_type: "Button"
```

## Scenario Changes

No changes required! The YAML format is the same:

```yaml
steps:
  - open_app:
      path: "C:\\MyApp\\app.exe"
  - click:
      element: my_button
```

## What If I Want to Keep Using the Old Package?

The old `uiauto` package is still present but deprecated. It will emit a `DeprecationWarning` when imported. We recommend migrating to the new structure for better maintainability and features.

## Benefits of Migration

1. **Smaller Dependencies**: Only install what you need
2. **Better Testing**: Each package has its own test suite
3. **Framework Choice**: Use QtQuick, JavaFX, or both
4. **Future-Proof**: Easy to add Electron, Avalonia, etc.
5. **Bug Fixes**: Core improvements benefit all implementations

## Need Help?

- Check package READMEs: `core/README.md`, `qtquick/README.md`, `javafx/README.md`
- See examples in `object-maps/` and `scenarios/`
- Open an issue on GitHub

## Timeline

- **Now**: Both old and new packages available
- **Future**: Old package will be removed in a future major version
