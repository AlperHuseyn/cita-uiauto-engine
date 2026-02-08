# uiauto_ui/commands.py
"""
CLI command specifications matching uiauto.cli exactly.
This is the single source of truth for UI form generation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from enum import Enum


class ArgType(Enum):
    """Argument types for UI widget selection."""
    PATH = "path"              # Existing file
    SAVE_PATH = "save_path"    # File to save (may not exist)
    DIR_PATH = "dir_path"      # Directory
    STRING = "string"          # Text input
    FLOAT = "float"            # Decimal number
    INT = "int"                # Integer
    BOOL = "bool"              # Checkbox/flag
    KEY_VALUE_LIST = "key_value_list"  # Table of key=value pairs


class Category(Enum):
    """Argument category for UI grouping."""
    BASIC = "basic"
    ADVANCED = "advanced"


@dataclass
class ArgSpec:
    """Specification for a single CLI argument."""
    name: str                                    # e.g., "elements"
    short: Optional[str] = None                  # e.g., "e"
    arg_type: ArgType = ArgType.STRING
    required: bool = False
    default: Any = None
    help_text: str = ""
    category: Category = Category.BASIC
    file_filter: str = "All Files (*)"           # For path types
    placeholder: str = ""                        # Placeholder text
    
    @property
    def cli_name(self) -> str:
        """Full CLI argument name (e.g., --elements)."""
        return f"--{self.name}"
    
    @property
    def cli_short(self) -> Optional[str]:
        """Short CLI argument name (e.g., -e)."""
        return f"-{self.short}" if self.short else None


@dataclass
class CommandSpec:
    """Specification for a CLI command."""
    name: str                           # Command name (e.g., "run")
    description: str                    # Help text
    args: List[ArgSpec] = field(default_factory=list)
    
    @property
    def required_args(self) -> List[ArgSpec]:
        return [a for a in self.args if a.required]
    
    @property
    def optional_args(self) -> List[ArgSpec]:
        return [a for a in self.args if not a.required]
    
    @property
    def basic_args(self) -> List[ArgSpec]:
        return [a for a in self.args if a.category == Category.BASIC]
    
    @property
    def advanced_args(self) -> List[ArgSpec]:
        return [a for a in self.args if a.category == Category.ADVANCED]


# =============================================================================
# Command Definitions (Matching cli.py EXACTLY)
# =============================================================================

RUN_COMMAND = CommandSpec(
    name="run",
    description="Run a YAML scenario using an elements.yaml object map",
    args=[
        # Required
        ArgSpec(
            name="elements", short="e",
            arg_type=ArgType.PATH, required=True,
            help_text="Path to elements.yaml (object map)",
            category=Category.BASIC,
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
        ),
        ArgSpec(
            name="scenario", short="s",
            arg_type=ArgType.PATH, required=False,
            help_text="Path to scenario.yaml",
            category=Category.BASIC,
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
        ),
        ArgSpec(
            name="scenarios-dir",
            arg_type=ArgType.DIR_PATH, required=False,
            help_text="Run all scenarios under directory",
            category=Category.BASIC,
            placeholder="Directory of scenarios",
        ),
        
        # Basic optional
        ArgSpec(
            name="app", short="a",
            arg_type=ArgType.PATH, required=False, default=None,
            help_text="Optional app path to start (can also use open_app step)",
            category=Category.BASIC,
            file_filter="Executables (*.exe);;All Files (*)",
        ),
        ArgSpec(
            name="report", short="r",
            arg_type=ArgType.SAVE_PATH, required=False, default="report.json",
            help_text="Report output path (JSON)",
            category=Category.BASIC,
            file_filter="JSON Files (*.json);;All Files (*)",
        ),
        ArgSpec(
            name="verbose",
            arg_type=ArgType.BOOL, required=False, default=False,
            help_text="Show detailed step output",
            category=Category.BASIC,
        ),
        
        # Advanced
        ArgSpec(
            name="schema",
            arg_type=ArgType.PATH, required=False,
            default="uiauto/schemas/scenario.schema.json",
            help_text="Path to scenario schema JSON",
            category=Category.ADVANCED,
            file_filter="JSON Files (*.json);;All Files (*)",
        ),
        ArgSpec(
            name="vars",
            arg_type=ArgType.PATH, required=False, default=None,
            help_text="Optional vars JSON file",
            category=Category.ADVANCED,
            file_filter="JSON Files (*.json);;All Files (*)",
        ),
        ArgSpec(
            name="var", short="v",
            arg_type=ArgType.KEY_VALUE_LIST, required=False, default=[],
            help_text="Variable in KEY=VALUE format (can be used multiple times)",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="timeout", short="t",
            arg_type=ArgType.FLOAT, required=False, default=None,
            help_text="Override default timeout in seconds",
            category=Category.ADVANCED,
            placeholder="10.0",
        ),
        ArgSpec(
            name="ci",
            arg_type=ArgType.BOOL, required=False, default=False,
            help_text="Use CI-optimized timeout settings",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="fast",
            arg_type=ArgType.BOOL, required=False, default=False,
            help_text="Use fast timeout settings for local development",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="slow",
            arg_type=ArgType.BOOL, required=False, default=False,
            help_text="Use slow timeout settings for unstable environments",
            category=Category.ADVANCED,
        ),
    ]
)


INSPECT_COMMAND = CommandSpec(
    name="inspect",
    description="Inspect Desktop UIA and dump control candidates (JSON/TXT)",
    args=[
        # Basic
        ArgSpec(
            name="window-title-re",
            arg_type=ArgType.STRING, required=False, default=None,
            help_text="Filter visible windows by title regex (best-effort)",
            category=Category.BASIC,
            placeholder="e.g., QtQuickTaskApp.*",
        ),
        ArgSpec(
            name="out", short="o",
            arg_type=ArgType.DIR_PATH, required=False, default="reports",
            help_text="Output directory for inspect reports",
            category=Category.BASIC,
        ),
        ArgSpec(
            name="query", short="q",
            arg_type=ArgType.STRING, required=False, default=None,
            help_text="Filter controls by contains; use 'regex:<pattern>' for regex search",
            category=Category.BASIC,
            placeholder="Filter by name, control_type, etc.",
        ),
        ArgSpec(
            name="emit-elements-yaml",
            arg_type=ArgType.SAVE_PATH, required=False, default=None,
            help_text="Write generated elements.yaml to this path",
            category=Category.BASIC,
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
        ),
        
        # Advanced
        ArgSpec(
            name="max-controls",
            arg_type=ArgType.INT, required=False, default=3000,
            help_text="Max number of descendants to scan",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="include-invisible",
            arg_type=ArgType.BOOL, required=False, default=False,
            help_text="Include invisible controls",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="exclude-disabled",
            arg_type=ArgType.BOOL, required=False, default=False,
            help_text="Exclude disabled controls",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="emit-window-name",
            arg_type=ArgType.STRING, required=False, default="main",
            help_text="Window name used in generated elements.yaml",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="state",
            arg_type=ArgType.STRING, required=False, default="default",
            help_text="UI state name",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="merge",
            arg_type=ArgType.BOOL, required=False, default=False,
            help_text="Merge with existing elements.yaml",
            category=Category.ADVANCED,
        ),
    ]
)


RECORD_COMMAND = CommandSpec(
    name="record",
    description="Record user interactions into semantic YAML steps",
    args=[
        # Required
        ArgSpec(
            name="elements", short="e",
            arg_type=ArgType.PATH, required=True,
            help_text="Path to elements.yaml (will be updated with new elements)",
            category=Category.BASIC,
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
        ),
        ArgSpec(
            name="scenario-out", short="s",
            arg_type=ArgType.SAVE_PATH, required=True,
            help_text="Output path for recorded scenario YAML",
            category=Category.BASIC,
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
        ),
        
        # Basic optional
        ArgSpec(
            name="window-title-re",
            arg_type=ArgType.STRING, required=False, default=None,
            help_text="Filter recording to window matching title regex",
            category=Category.BASIC,
            placeholder="Limit recording to matching window",
        ),
        
        # Advanced
        ArgSpec(
            name="window-name",
            arg_type=ArgType.STRING, required=False, default="main",
            help_text="Window name for element specs",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="state",
            arg_type=ArgType.STRING, required=False, default="default",
            help_text="UI state name for recorded elements",
            category=Category.ADVANCED,
        ),
        ArgSpec(
            name="debug-json-out",
            arg_type=ArgType.SAVE_PATH, required=False, default=None,
            help_text="Save debug snapshots to this JSON file",
            category=Category.ADVANCED,
            file_filter="JSON Files (*.json);;All Files (*)",
        ),
    ]
)


VALIDATE_COMMAND = CommandSpec(
    name="validate",
    description="Validate configuration files",
    args=[
        ArgSpec(
            name="elements", short="e",
            arg_type=ArgType.PATH, required=True,
            help_text="Path to elements.yaml file",
            category=Category.BASIC,
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
        ),
        ArgSpec(
            name="scenario", short="s",
            arg_type=ArgType.PATH, required=False, default=None,
            help_text="Path to scenario YAML file (optional)",
            category=Category.BASIC,
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
        ),
        ArgSpec(
            name="scenarios-dir",
            arg_type=ArgType.DIR_PATH, required=False, default=None,
            help_text="Validate all scenarios under directory",
            category=Category.BASIC,
            placeholder="Directory of scenarios",
        ),
        ArgSpec(
            name="schema",
            arg_type=ArgType.PATH, required=False, default=None,
            help_text="Path to scenario JSON schema",
            category=Category.ADVANCED,
            file_filter="JSON Files (*.json);;All Files (*)",
        ),
    ]
)


LIST_ELEMENTS_COMMAND = CommandSpec(
    name="list-elements",
    description="List all defined windows and elements",
    args=[
        ArgSpec(
            name="elements", short="e",
            arg_type=ArgType.PATH, required=True,
            help_text="Path to elements.yaml file",
            category=Category.BASIC,
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
        ),
    ]
)


# =============================================================================
# Command Registry
# =============================================================================

COMMANDS: Dict[str, CommandSpec] = {
    "run": RUN_COMMAND,
    "inspect": INSPECT_COMMAND,
    "record": RECORD_COMMAND,
    "validate": VALIDATE_COMMAND,
    "list-elements": LIST_ELEMENTS_COMMAND,
}


def get_command(name: str) -> CommandSpec:
    """Get command specification by name."""
    if name not in COMMANDS:
        raise ValueError(f"Unknown command: {name}. Available: {list(COMMANDS.keys())}")
    return COMMANDS[name]


# =============================================================================
# Argument Builder
# =============================================================================

class ArgBuilder:
    """Builds CLI argv from form values."""
    
    def __init__(self, command: CommandSpec):
        self.command = command
        self._values: Dict[str, Any] = {}
    
    def set(self, name: str, value: Any) -> "ArgBuilder":
        """Set argument value."""
        self._values[name] = value
        return self
    
    def build(self) -> List[str]:
        """Build argv list."""
        argv = [self.command.name]
        
        for arg in self.command.args:
            value = self._values.get(arg.name)
            
            # Skip None/empty values
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, list) and not value:
                continue
            
            # Skip default values for optional args
            if not arg.required and value == arg.default:
                continue
            
            # Build argument
            if arg.arg_type == ArgType.BOOL:
                if value:
                    argv.append(arg.cli_name)
            elif arg.arg_type == ArgType.KEY_VALUE_LIST:
                for item in value:
                    argv.extend([arg.cli_name, item])
            else:
                argv.extend([arg.cli_name, str(value)])
        
        return argv
    
    def validate(self) -> tuple:
        """Validate required arguments. Returns (is_valid, error_message)."""
        for arg in self.command.required_args:
                value = self._values.get(arg.name)
                if value is None or (isinstance(value, str) and not value.strip()):
                        return False, f"{arg.name} is required"

                # Check file exists for PATH type
                if arg.arg_type == ArgType.PATH:
                        import os
                        if not os.path.exists(value):
                                return False, f"File not found: {value}"
        
        return True, ""