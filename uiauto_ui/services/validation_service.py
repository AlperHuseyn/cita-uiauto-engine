# uiauto_ui/services/validation_service.py
"""
Validation service for form inputs and files.
Centralizes all validation logic.
"""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def error_message(self) -> str:
        """First error message, or empty string."""
        return self.errors[0] if self.errors else ""
    
    @property
    def all_messages(self) -> str:
        """All errors and warnings as formatted string."""
        messages = []
        for error in self.errors:
            messages.append(f"❌ {error}")
        for warning in self.warnings:
            messages.append(f"⚠️ {warning}")
        return "\n".join(messages)
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def merge(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


class ValidationService:
    """
    Service for validating form inputs and files.
    
    Provides methods for:
    - File existence checks
    - YAML/JSON syntax validation
    - Required field validation
    - Path validation
    - Command-specific validation
    """
    
    def __init__(self):
        self._yaml_available = self._check_yaml_available()
    
    def _check_yaml_available(self) -> bool:
        """Check if PyYAML is available."""
        try:
            import yaml
            return True
        except ImportError:
            logger.warning("PyYAML not available, YAML validation disabled")
            return False
    
    # -------------------------------------------------------------------------
    # Basic Validators
    # -------------------------------------------------------------------------
    
    def validate_required(self, value: Any, field_name: str) -> ValidationResult:
        """
        Validate that a required field has a value.
        
        Args:
            value: The value to check
            field_name: Name of the field for error message
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if value is None:
            result.add_error(f"{field_name} is required")
        elif isinstance(value, str) and not value.strip():
            result.add_error(f"{field_name} is required")
        elif isinstance(value, (list, dict)) and len(value) == 0:
            result.add_error(f"{field_name} is required")
        
        return result
    
    def validate_file_exists(self, path: str, field_name: str) -> ValidationResult:
        """
        Validate that a file exists.
        
        Args:
            path: File path to check
            field_name: Name of the field for error message
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not path or not path.strip():
            result.add_error(f"{field_name} is required")
            return result
        
        path_obj = Path(path)
        
        if not path_obj.exists():
            result.add_error(f"File not found: {path}")
        elif not path_obj.is_file():
            result.add_error(f"Not a file: {path}")
        
        return result
    
    def validate_directory_exists(self, path: str, field_name: str) -> ValidationResult:
        """
        Validate that a directory exists (or can be created).
        
        Args:
            path: Directory path to check
            field_name: Name of the field for error message
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not path or not path.strip():
            result.add_error(f"{field_name} is required")
            return result
        
        path_obj = Path(path)
        
        if path_obj.exists() and not path_obj.is_dir():
            result.add_error(f"Not a directory: {path}")
        elif not path_obj.exists():
            # Check if parent exists and we can create it
            if not path_obj.parent.exists():
                result.add_warning(f"Directory will be created: {path}")
        
        return result
    
    def validate_save_path(self, path: str, field_name: str) -> ValidationResult:
        """
        Validate a path for saving a file.
        
        Args:
            path: File path to check
            field_name: Name of the field for error message
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not path or not path.strip():
            result.add_error(f"{field_name} is required")
            return result
        
        path_obj = Path(path)
        
        # Check parent directory
        if not path_obj.parent.exists():
            result.add_warning(f"Directory will be created: {path_obj.parent}")
        
        # Check if file already exists
        if path_obj.exists():
            result.add_warning(f"File will be overwritten: {path}")
        
        return result
    
    def validate_yaml_file(self, path: str, field_name: str) -> ValidationResult:
        """
        Validate that a file exists and is valid YAML.
        
        Args:
            path: File path to check
            field_name: Name of the field for error message
            
        Returns:
            ValidationResult
        """
        result = self.validate_file_exists(path, field_name)
        
        if not result.is_valid:
            return result
        
        if not self._yaml_available:
            result.add_warning("YAML syntax validation skipped (PyYAML not installed)")
            return result
        
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            result.add_error(f"Invalid YAML syntax in {field_name}: {e}")
        except UnicodeDecodeError as e:
            result.add_error(f"Encoding error in {field_name}: {e}")
        except Exception as e:
            result.add_error(f"Could not read {field_name}: {e}")
        
        return result
    
    def validate_json_file(self, path: str, field_name: str) -> ValidationResult:
        """
        Validate that a file exists and is valid JSON.
        
        Args:
            path: File path to check
            field_name: Name of the field for error message
            
        Returns:
            ValidationResult
        """
        result = self.validate_file_exists(path, field_name)
        
        if not result.is_valid:
            return result
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON syntax in {field_name}: {e}")
        except UnicodeDecodeError as e:
            result.add_error(f"Encoding error in {field_name}: {e}")
        except Exception as e:
            result.add_error(f"Could not read {field_name}: {e}")
        
        return result
    
    # -------------------------------------------------------------------------
    # Command-Specific Validators
    # -------------------------------------------------------------------------
    
    def validate_command(self, command: str, values: Dict[str, Any]) -> ValidationResult:
        """
        Validate form values for a specific command.
        
        This is the main entry point used by forms.
        
        Args:
            command: Command name (run, inspect, record, etc.)
            values: Dictionary of form values
            
        Returns:
            ValidationResult with all errors and warnings
        """
        validators = {
            "run": self._validate_run_values,
            "inspect": self._validate_inspect_values,
            "record": self._validate_record_values,
            "validate": self._validate_validate_values,
            "list-elements": self._validate_list_elements_values,
        }
        
        validator = validators.get(command)
        if validator is None:
            result = ValidationResult(is_valid=True)
            result.add_warning(f"No validation defined for command: {command}")
            return result
        
        return validator(values)
    
    def _validate_run_values(self, values: Dict[str, Any]) -> ValidationResult:
        """Validate 'run' command values."""
        result = ValidationResult(is_valid=True)
        
        # Required: elements
        elements = values.get("elements", "")
        if elements:
            result.merge(self.validate_yaml_file(elements, "Elements file"))
        else:
            result.add_error("Elements file is required")
        
        # Required: scenario
        scenario = values.get("scenario", "")
        if scenario:
            result.merge(self.validate_yaml_file(scenario, "Scenario file"))
        else:
            result.add_error("Scenario file is required")
        
        # Optional: app
        app = values.get("app", "")
        if app:
            result.merge(self.validate_file_exists(app, "Application"))
        
        # Optional: schema
        schema = values.get("schema", "")
        if schema:
            result.merge(self.validate_json_file(schema, "Schema file"))
        
        # Optional: vars file
        vars_file = values.get("vars", "")
        if vars_file:
            result.merge(self.validate_json_file(vars_file, "Vars file"))
        
        return result
    
    def _validate_inspect_values(self, values: Dict[str, Any]) -> ValidationResult:
        """Validate 'inspect' command values."""
        result = ValidationResult(is_valid=True)
        
        # Optional: output directory
        out_dir = values.get("out", "")
        if out_dir:
            result.merge(self.validate_directory_exists(out_dir, "Output directory"))
        
        # Optional: emit yaml path
        emit_yaml = values.get("emit-elements-yaml", "")
        if emit_yaml:
            result.merge(self.validate_save_path(emit_yaml, "Elements output"))
        
        return result
    
    def _validate_record_values(self, values: Dict[str, Any]) -> ValidationResult:
        """Validate 'record' command values."""
        result = ValidationResult(is_valid=True)
        
        # Required: elements
        elements = values.get("elements", "")
        if elements:
            result.merge(self.validate_yaml_file(elements, "Elements file"))
        else:
            result.add_error("Elements file is required")
        
        # Required: scenario-out
        scenario_out = values.get("scenario-out", "")
        if scenario_out:
            result.merge(self.validate_save_path(scenario_out, "Scenario output"))
        else:
            result.add_error("Scenario output path is required")
        
        # Optional: debug-json-out
        debug_json = values.get("debug-json-out", "")
        if debug_json:
            result.merge(self.validate_save_path(debug_json, "Debug JSON output"))
        
        return result
    
    def _validate_validate_values(self, values: Dict[str, Any]) -> ValidationResult:
        """Validate 'validate' command values."""
        result = ValidationResult(is_valid=True)
        
        # Required: elements
        elements = values.get("elements", "")
        if elements:
            result.merge(self.validate_yaml_file(elements, "Elements file"))
        else:
            result.add_error("Elements file is required")
        
        # Optional: scenario
        scenario = values.get("scenario", "")
        if scenario:
            result.merge(self.validate_yaml_file(scenario, "Scenario file"))
        
        return result
    
    def _validate_list_elements_values(self, values: Dict[str, Any]) -> ValidationResult:
        """Validate 'list-elements' command values."""
        result = ValidationResult(is_valid=True)
        
        # Required: elements
        elements = values.get("elements", "")
        if elements:
            result.merge(self.validate_yaml_file(elements, "Elements file"))
        else:
            result.add_error("Elements file is required")
        
        return result
    
    # -------------------------------------------------------------------------
    # Legacy Methods (for backward compatibility)
    # -------------------------------------------------------------------------
    
    def validate_run_command(
        self,
        elements_path: str,
        scenario_path: str,
        app_path: Optional[str] = None,
    ) -> ValidationResult:
        """Validate inputs for the 'run' command."""
        return self._validate_run_values({
            "elements": elements_path,
            "scenario": scenario_path,
            "app": app_path,
        })
    
    def validate_record_command(
        self,
        elements_path: str,
        scenario_out: str,
    ) -> ValidationResult:
        """Validate inputs for the 'record' command."""
        return self._validate_record_values({
            "elements": elements_path,
            "scenario-out": scenario_out,
        })