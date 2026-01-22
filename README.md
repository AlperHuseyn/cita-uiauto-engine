# UIAuto Engine - Monorepo

Multi-framework desktop UI automation toolkit with framework-agnostic core and specialized implementations.

## 📦 Packages

This monorepo contains three packages:

### 1. **core/** - Framework-Agnostic Engine
- YAML-based object maps (elements.yaml)
- Scenario runner with JSON schema validation
- Abstract interfaces for implementations

### 2. **qtquick/** - QtQuick/QML Automation
- Windows UI Automation support via pywinauto
- QtQuick/QML element resolution via `Accessible.name`
- Inspector and recorder tools

### 3. **javafx/** - JavaFX Automation ⚠️ Alpha
- Java Accessibility API integration
- Cross-platform support
- Basic automation operations

## 🚀 Installation

```bash
# QtQuick Only
pip install ./core ./qtquick

# JavaFX Only
pip install ./core ./javafx

# Development mode
pip install -e ./core -e ./qtquick -e ./javafx
```

## 📖 Usage

See individual package READMEs for details:
- [core/README.md](core/README.md)
- [qtquick/README.md](qtquick/README.md)
- [javafx/README.md](javafx/README.md)

## License

MIT
