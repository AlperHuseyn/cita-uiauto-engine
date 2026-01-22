# UIAuto Core

Framework-agnostic core for UI automation.

## Overview

`uiauto-core` provides the fundamental building blocks for UI automation frameworks:

- **Interfaces**: Abstract base classes for framework implementations (ISession, IResolver, IElement, IInspector, IActions)
- **Repository**: YAML-based object map parser for semantic element naming
- **Runner**: Scenario executor that validates and runs YAML test scenarios
- **Waits**: Retry/polling utilities for robust element interaction
- **Exceptions**: Comprehensive error hierarchy with detailed diagnostics

## Installation

```bash
pip install ./core
```

Or for development:

```bash
pip install -e ./core[dev]
```

## Usage

`uiauto-core` is not meant to be used directly. Instead, install a framework-specific implementation:

- **uiauto-qtquick**: For QtQuick/QML and Windows UIA applications
- **uiauto-javafx**: For JavaFX applications via Java Access Bridge

## Creating a Framework Implementation

To add support for a new UI framework:

1. Implement the core interfaces:
   - `ISession`: Application lifecycle management
   - `IResolver`: Element resolution from object maps
   - `IElement`: Element interaction API
   - `IInspector`: UI tree inspection
   - `IActions`: High-level keyword actions

2. Use `Repository` to parse elements.yaml object maps
3. Use `Runner` to execute scenario.yaml test scenarios
4. Use `wait_until` for reliable element synchronization

See `uiauto-qtquick` and `uiauto-javafx` packages for reference implementations.

## License

MIT
