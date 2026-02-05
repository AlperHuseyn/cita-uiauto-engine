# uiauto_ui/forms/run_form.py
"""
Form for 'uiauto run' command.
Executes YAML scenarios using element maps.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QCheckBox, QDoubleSpinBox, QPushButton
)
from PySide6.QtCore import Signal

from .base_form import BaseCommandForm
from ..widgets.path_selector import PathSelector
from ..widgets.key_value_table import KeyValueTable


class RunForm(BaseCommandForm):
    """
    Form for the 'run' command.
    
    Collects:
    - Required: elements.yaml, scenario.yaml
    - Optional: app path, report path, verbose
    - Advanced: timeout, CI mode, fast mode, schema, vars
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
    
    def _get_command_name(self) -> str:
        return "run"
    
    def _build_form(self) -> None:
        """Build the run form UI."""
        
        # === Required Section ===
        required_group, required_layout = self._create_group("Required")
        
        self._elements_path = PathSelector(
            mode="file",
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
            placeholder="Path to elements.yaml"
        )
        self._elements_path.path_changed.connect(self._update_preview)
        self._register_widget("elements", self._elements_path)
        required_layout.addRow("Elements:", self._elements_path)
        
        self._scenario_path = PathSelector(
            mode="file",
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
            placeholder="Path to scenario.yaml"
        )
        self._scenario_path.path_changed.connect(self._update_preview)
        self._register_widget("scenario", self._scenario_path)
        required_layout.addRow("Scenario:", self._scenario_path)
        
        self._main_layout.addWidget(required_group)
        
        # === Options Section ===
        options_group, options_layout = self._create_group("Options")
        
        self._app_path = PathSelector(
            mode="file",
            file_filter="Executables (*.exe);;All Files (*)",
            placeholder="Optional: Application to launch"
        )
        self._app_path.path_changed.connect(self._update_preview)
        self._register_widget("app", self._app_path)
        options_layout.addRow("App Path:", self._app_path)
        
        self._report_path = PathSelector(
            mode="save",
            file_filter="JSON Files (*.json);;All Files (*)",
            placeholder="report.json"
        )
        self._report_path.set_value("report.json")
        self._report_path.path_changed.connect(self._update_preview)
        self._register_widget("report", self._report_path)
        options_layout.addRow("Report:", self._report_path)
        
        self._verbose_cb = QCheckBox("Verbose output")
        self._verbose_cb.stateChanged.connect(self._update_preview)
        self._register_widget("verbose", self._verbose_cb)
        options_layout.addRow("", self._verbose_cb)
        
        self._main_layout.addWidget(options_group)
        
        # === Advanced Section (Collapsible) ===
        advanced_group, advanced_layout = self._create_collapsible_group(
            "Advanced Settings", 
            collapsed=True
        )
        
        # Timeout
        self._timeout_spin = QDoubleSpinBox()
        self._timeout_spin.setRange(0, 300)
        self._timeout_spin.setDecimals(1)
        self._timeout_spin.setSingleStep(1.0)
        self._timeout_spin.setSpecialValueText("Default")
        self._timeout_spin.setValue(0)
        self._timeout_spin.setToolTip("Override default timeout in seconds")
        self._timeout_spin.valueChanged.connect(self._update_preview)
        self._register_widget("timeout", self._timeout_spin)
        advanced_layout.addRow("Timeout (s):", self._timeout_spin)
        
        # Mode flags
        mode_layout = QHBoxLayout()
        
        self._ci_cb = QCheckBox("CI Mode")
        self._ci_cb.setToolTip("Use CI-optimized timeout settings")
        self._ci_cb.stateChanged.connect(self._update_preview)
        self._register_widget("ci", self._ci_cb)
        mode_layout.addWidget(self._ci_cb)
        
        self._fast_cb = QCheckBox("Fast Mode")
        self._fast_cb.setToolTip("Use fast timeout settings for local dev")
        self._fast_cb.stateChanged.connect(self._update_preview)
        self._register_widget("fast", self._fast_cb)
        mode_layout.addWidget(self._fast_cb)
        
        mode_layout.addStretch()
        advanced_layout.addRow("", mode_layout)
        
        # Schema path
        self._schema_path = PathSelector(
            mode="file",
            file_filter="JSON Files (*.json);;All Files (*)",
            placeholder="Custom scenario schema"
        )
        self._schema_path.path_changed.connect(self._update_preview)
        self._register_widget("schema", self._schema_path)
        advanced_layout.addRow("Schema:", self._schema_path)
        
        # Vars file
        self._vars_path = PathSelector(
            mode="file",
            file_filter="JSON Files (*.json);;All Files (*)",
            placeholder="Variables JSON file"
        )
        self._vars_path.path_changed.connect(self._update_preview)
        self._register_widget("vars", self._vars_path)
        advanced_layout.addRow("Vars File:", self._vars_path)
        
        # Inline vars
        self._var_table = KeyValueTable()
        self._var_table.values_changed.connect(self._update_preview)
        self._register_widget("var", self._var_table)
        advanced_layout.addRow("Inline Vars:", self._var_table)
        
        self._main_layout.addWidget(advanced_group)
    
    def _create_run_button(self) -> QPushButton:
        """Create run button with green styling."""
        btn = QPushButton("Run Scenario")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 24px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #9E9E9E;
            }
        """)
        return btn
    
    def _collect_values(self) -> Dict[str, Any]:
        """Collect all form values."""
        values = {
            "elements": self._elements_path.value(),
            "scenario": self._scenario_path.value(),
            "app": self._app_path.value(),
            "report": self._report_path.value(),
            "verbose": self._verbose_cb.isChecked(),
            "schema": self._schema_path.value(),
            "vars": self._vars_path.value(),
            "var": self._var_table.values(),
        }
        
        # Timeout: only include if > 0
        timeout = self._timeout_spin.value()
        if timeout > 0:
            values["timeout"] = timeout
        
        # Mode flags
        if self._ci_cb.isChecked():
            values["ci"] = True
        if self._fast_cb.isChecked():
            values["fast"] = True
        
        return values
    
    def set_values(self, values: Dict[str, Any]) -> None:
        """Populate form from values dictionary."""
        if "elements" in values:
            self._elements_path.set_value(values["elements"])
        if "scenario" in values:
            self._scenario_path.set_value(values["scenario"])
        if "app" in values:
            self._app_path.set_value(values["app"])
        if "report" in values:
            self._report_path.set_value(values["report"])
        if "verbose" in values:
            self._verbose_cb.setChecked(values["verbose"])
        if "timeout" in values:
            self._timeout_spin.setValue(values["timeout"])
        if "ci" in values:
            self._ci_cb.setChecked(values["ci"])
        if "fast" in values:
            self._fast_cb.setChecked(values["fast"])
        if "schema" in values:
            self._schema_path.set_value(values["schema"])
        if "vars" in values:
            self._vars_path.set_value(values["vars"])
        if "var" in values:
            self._var_table.set_values(values["var"])
        
        self._update_preview()
    
    def reset(self) -> None:
        """Reset form to defaults."""
        self._elements_path.clear()
        self._scenario_path.clear()
        self._app_path.clear()
        self._report_path.set_value("report.json")
        self._verbose_cb.setChecked(False)
        self._timeout_spin.setValue(0)
        self._ci_cb.setChecked(False)
        self._fast_cb.setChecked(False)
        self._schema_path.clear()
        self._vars_path.clear()
        self._var_table.clear()
        self._update_preview()
    
    # -------------------------------------------------------------------------
    # Settings Integration
    # -------------------------------------------------------------------------
    
    def load_last_paths(self, settings_service) -> None:
        """Load last used paths from settings."""
        elements = settings_service.load_last_elements()
        if elements:
            self._elements_path.set_value(elements)
        
        scenario = settings_service.load_last_scenario()
        if scenario:
            self._scenario_path.set_value(scenario)
        
        report = settings_service.load_last_report()
        if report:
            self._report_path.set_value(report)
        
        app = settings_service.load_last_app()
        if app:
            self._app_path.set_value(app)
        
        self._update_preview()
    
    def save_last_paths(self, settings_service) -> None:
        """Save current paths to settings."""
        elements = self._elements_path.value()
        if elements:
            settings_service.save_last_elements(elements)
        
        scenario = self._scenario_path.value()
        if scenario:
            settings_service.save_last_scenario(scenario)
        
        report = self._report_path.value()
        if report:
            settings_service.save_last_report(report)
        
        app = self._app_path.value()
        if app:
            settings_service.save_last_app(app)