# UIAuto Core

Framework-agnostic UI automation engine providing core functionality for YAML-based test scenarios.

## Features

- **Repository**: Load and validate YAML object maps (elements.yaml)
- **Runner**: Execute YAML scenario files with variable substitution
- **Waits**: Robust retry/polling utilities for flaky UI interactions
- **Exceptions**: Rich exception hierarchy with context and artifacts
- **Interfaces**: Abstract base classes for framework implementations
- **Artifacts**: Screenshot and control tree dump utilities

## Installation

```bash
pip install ./core
```

Or in development mode:

```bash
pip install -e ./core
```

## Usage

The core package is meant to be used by framework-specific implementations (qtquick, javafx, etc.). It provides the foundation but does not contain any UI automation logic itself.

### For Framework Implementers

To create a new framework implementation:

1. Implement `ISession` interface for application lifecycle management
2. Implement `IElement` interface for UI element interactions
3. Implement `IResolver` interface for element resolution from object maps
4. Create an Actions class that uses your IResolver
5. Use the Runner class to execute scenarios with your implementations

Example:

```python
from uiauto_core import Repository, Runner
from your_framework import YourSession, YourResolver, YourActions

# Load object map
repo = Repository("elements.yaml")

# Create runner with schema
runner = Runner(repo, schema_path="path/to/scenario.schema.json")

# Create framework-specific instances
session = YourSession(backend="your_backend")
resolver = YourResolver(session, repo)
actions = YourActions(resolver)

# Run scenario
report = runner.run(
    scenario_path="scenario.yaml",
    session=session,
    resolver=resolver,
    actions=actions,
    app_path="/path/to/app.exe"
)

print(report["status"])  # "passed" or "failed"
```

## API Reference

### Repository

```python
from uiauto_core import Repository

repo = Repository("elements.yaml")
app_config = repo.app  # AppConfig with timeout, backend, etc.
window_spec = repo.get_window_spec("main_window")
element_spec = repo.get_element_spec("submit_button")
```

### Runner

```python
from uiauto_core import Runner

runner = Runner(repo, schema_path="scenario.schema.json")
report = runner.run(
    scenario_path="test.yaml",
    session=session,
    resolver=resolver,
    actions=actions
)
```

### Waits

```python
from uiauto_core import wait_until

result = wait_until(
    predicate=lambda: element.is_visible(),
    timeout=10.0,
    interval=0.2,
    description="element visible"
)
```

## License

MIT
