# UIAuto Core

Framework-agnostic UI automation engine providing YAML-based scenario execution, object mapping, and wait utilities.

## Features

- **Repository**: YAML-based object map loader with validation
- **Runner**: Scenario execution engine with variable substitution
- **Waits**: Polling-based wait utilities with timeout handling
- **Exceptions**: Rich error types with debugging artifacts
- **Interfaces**: Abstract base classes for framework implementations

## Installation

```bash
pip install ./core
```

## Usage

This is a core library. Use with a framework-specific implementation:
- `uiauto-qtquick` - For QtQuick/WPF applications (pywinauto UIA)
- `uiauto-javafx` - For JavaFX applications (Java Access Bridge)

## Architecture

Core provides the framework-agnostic automation engine. Framework-specific packages implement:
- `ISession` - Application connection and window management
- `IResolver` - Element resolution from object maps
- `IElement` - Element interaction wrapper
