# uiauto_ui/forms/run_form.py
"""
Form for 'uiauto run' command.
Executes YAML scenarios using element maps.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDoubleSpinBox,
                               QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QRadioButton,
                               QVBoxLayout, QWidget)

from ..widgets.key_value_table import KeyValueTable
from ..widgets.path_selector import PathSelector
from .base_form import BaseCommandForm


class RunForm(BaseCommandForm):
    """
    Form for the 'run' command.
    
    Collects:
    - Required: elements.yaml, scenario.yaml
    - Optional: app path, report path, verbose
    - Advanced: timeout, CI mode, fast mode, schema, vars
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        self._mode = "single"
        self._updating_mode = False
        self._validation_state = "needs_validation"
        super().__init__(parent)
        self._set_validation_state("needs_validation")
    
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
        self._elements_path.path_changed.connect(self._on_inputs_changed)
        self._register_widget("elements", self._elements_path)
        required_layout.addRow("Elements:", self._elements_path)
        
        self._scenario_path = PathSelector(
            mode="file",
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
            placeholder="Path to scenario.yaml"
        )
        self._scenario_path.setToolTip("Provide either a scenario file or a scenarios directory")
        self._scenario_path.path_changed.connect(self._on_scenario_path_changed)
        self._register_widget("scenario", self._scenario_path)

        self._scenarios_dir = PathSelector(
            mode="dir",
            file_filter="",
            placeholder="Path to scenarios directory"
        )
        self._scenarios_dir.setToolTip("Provide either a scenario file or a scenarios directory")
        self._scenarios_dir.path_changed.connect(self._on_scenarios_dir_changed)
        self._register_widget("scenarios-dir", self._scenarios_dir)

        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(10)

        self._mode_group = QButtonGroup(self)
        self._single_mode_rb = QRadioButton("Scenario File")
        self._single_mode_rb.setToolTip("Run a single scenario file")
        self._bulk_mode_rb = QRadioButton("Scenarios Dir")
        self._bulk_mode_rb.setToolTip("Run all YAML scenarios in a directory")

        self._mode_group.addButton(self._single_mode_rb)
        self._mode_group.addButton(self._bulk_mode_rb)
        self._single_mode_rb.toggled.connect(self._on_mode_toggled)
        self._bulk_mode_rb.toggled.connect(self._on_mode_toggled)

        mode_layout.addWidget(self._single_mode_rb)
        mode_layout.addWidget(self._bulk_mode_rb)
        mode_layout.addStretch()

        required_layout.addRow("Mode:", mode_widget)
        required_layout.addRow("Scenario:", self._scenario_path)
        required_layout.addRow("Scenarios Dir:", self._scenarios_dir)

        self._validation_status = QLabel()
        required_layout.addRow("Validation:", self._validation_status)
        
        self._main_layout.addWidget(required_group)
        self._set_mode("single", clear_other=False)
        
        # === Options Section ===
        options_group, options_layout = self._create_group("Options")
        
        self._app_path = PathSelector(
            mode="file",
            file_filter="Executables (*.exe);;All Files (*)",
            placeholder="Optional: Application to launch"
        )
        self._app_path.path_changed.connect(self._on_inputs_changed)
        self._register_widget("app", self._app_path)
        options_layout.addRow("App Path:", self._app_path)
        
        self._report_path = PathSelector(
            mode="save",
            file_filter="JSON Files (*.json);;All Files (*)",
            placeholder="report.json"
        )
        self._report_path.set_value("report.json")
        self._report_path.path_changed.connect(self._on_inputs_changed)
        self._register_widget("report", self._report_path)
        options_layout.addRow("Report:", self._report_path)
        
        self._verbose_cb = QCheckBox("Verbose output")
        self._verbose_cb.stateChanged.connect(self._on_inputs_changed)
        self._register_widget("verbose", self._verbose_cb)
        options_layout.addRow("", self._verbose_cb)

        self._action_logging_cb = QCheckBox("Live Action Logging")
        self._action_logging_cb.setToolTip("Stream action logs during scenario execution")
        self._action_logging_cb.stateChanged.connect(self._on_action_logging_toggled)
        self._register_widget("action-logging", self._action_logging_cb)
        options_layout.addRow("", self._action_logging_cb)

        self._timing_logging_cb = QCheckBox("Timing Debug Logs")
        self._timing_logging_cb.setToolTip("Show wait/retry timing events in output (dev mode)")
        self._timing_logging_cb.stateChanged.connect(self._on_timing_logging_toggled)
        self._register_widget("timing-logging", self._timing_logging_cb)
        options_layout.addRow("", self._timing_logging_cb)
        
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
        self._timeout_spin.valueChanged.connect(self._on_inputs_changed)
        self._register_widget("timeout", self._timeout_spin)
        advanced_layout.addRow("Timeout (s):", self._timeout_spin)
        
        # Preset flags
        preset_layout = QHBoxLayout()

        self._preset_group = QButtonGroup(self)
        self._preset_default_rb = QRadioButton("Default")
        self._preset_default_rb.setToolTip("Use default timing preset")
        self._preset_fast_rb = QRadioButton("Fast")
        self._preset_fast_rb.setToolTip("Use fast timeout settings for local dev")
        self._preset_slow_rb = QRadioButton("Slow")
        self._preset_slow_rb.setToolTip("Use slow timeout settings for unstable environments")
        self._preset_ci_rb = QRadioButton("CI")
        self._preset_ci_rb.setToolTip("Use CI-optimized timeout settings")

        self._preset_group.addButton(self._preset_default_rb)
        self._preset_group.addButton(self._preset_fast_rb)
        self._preset_group.addButton(self._preset_slow_rb)
        self._preset_group.addButton(self._preset_ci_rb)
        self._preset_default_rb.setChecked(True)

        self._register_widget("preset-default", self._preset_default_rb)
        self._register_widget("preset-fast", self._preset_fast_rb)
        self._register_widget("preset-slow", self._preset_slow_rb)
        self._register_widget("preset-ci", self._preset_ci_rb)

        for btn in (
            self._preset_default_rb,
            self._preset_fast_rb,
            self._preset_slow_rb,
            self._preset_ci_rb,
        ):
            btn.toggled.connect(self._on_inputs_changed)
            preset_layout.addWidget(btn)

        preset_layout.addStretch()
        advanced_layout.addRow("Preset:", preset_layout)
        
        # Schema path
        self._schema_path = PathSelector(
            mode="file",
            file_filter="JSON Files (*.json);;All Files (*)",
            placeholder="Custom scenario schema"
        )
        self._schema_path.path_changed.connect(self._on_inputs_changed)
        self._register_widget("schema", self._schema_path)
        advanced_layout.addRow("Schema:", self._schema_path)
        
        # Vars file
        self._vars_path = PathSelector(
            mode="file",
            file_filter="JSON Files (*.json);;All Files (*)",
            placeholder="Variables JSON file"
        )
        self._vars_path.path_changed.connect(self._on_inputs_changed)
        self._register_widget("vars", self._vars_path)
        advanced_layout.addRow("Vars File:", self._vars_path)
        
        # Inline vars
        self._var_table = KeyValueTable()
        self._var_table.values_changed.connect(self._on_inputs_changed)
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
            "scenario": self._scenario_path.value() if self._mode == "single" else "",
            "scenarios-dir": self._scenarios_dir.value() if self._mode == "bulk" else "",
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
        if self._preset_ci_rb.isChecked():
            values["ci"] = True
        elif self._preset_slow_rb.isChecked():
            values["slow"] = True
        elif self._preset_fast_rb.isChecked():
            values["fast"] = True
        
        return values

    def _collect_validate_values(self) -> Dict[str, Any]:
        """Collect values for validate command."""
        values = {
            "elements": self._elements_path.value(),
            "scenario": self._scenario_path.value() if self._mode == "single" else "",
            "scenarios-dir": self._scenarios_dir.value() if self._mode == "bulk" else "",
            "schema": self._schema_path.value(),
        }
        return values
    
    def set_values(self, values: Dict[str, Any]) -> None:
        """Populate form from values dictionary."""
        if "elements" in values:
            self._elements_path.set_value(values["elements"])
        if "scenario" in values:
            self._scenario_path.set_value(values["scenario"])
        if "scenarios-dir" in values:
            self._scenarios_dir.set_value(values["scenarios-dir"])
        if "app" in values:
            self._app_path.set_value(values["app"])
        if "report" in values:
            self._report_path.set_value(values["report"])
        if "verbose" in values:
            self._verbose_cb.setChecked(values["verbose"])
        if "timeout" in values:
            self._timeout_spin.setValue(values["timeout"])
        if values.get("ci"):
            self._preset_ci_rb.setChecked(True)
        elif values.get("slow"):
            self._preset_slow_rb.setChecked(True)
        elif values.get("fast"):
            self._preset_fast_rb.setChecked(True)
        else:
            self._preset_default_rb.setChecked(True)
        if "schema" in values:
            self._schema_path.set_value(values["schema"])
        if "vars" in values:
            self._vars_path.set_value(values["vars"])
        if "var" in values:
            self._var_table.set_values(values["var"])

        self._set_mode("bulk" if self._scenarios_dir.value() else "single", clear_other=False)
        self._invalidate_validation()
        self._update_preview()
    
    def reset(self) -> None:
        """Reset form to defaults."""
        self._elements_path.clear()
        self._scenario_path.clear()
        self._scenarios_dir.clear()
        self._app_path.clear()
        self._report_path.set_value("report.json")
        self._verbose_cb.setChecked(False)
        self._action_logging_cb.setChecked(False)
        self._timing_logging_cb.setChecked(False)
        self._timeout_spin.setValue(0)
        self._preset_default_rb.setChecked(True)
        
        self._schema_path.clear()
        self._vars_path.clear()
        self._var_table.clear()
        self._set_mode("single", clear_other=True)
        self._invalidate_validation()
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
        scenarios_dir = settings_service.load_last_scenarios_dir()
        last_mode = settings_service.load_last_scenario_mode()

        if last_mode == "bulk" and scenarios_dir:
            self._scenarios_dir.set_value(scenarios_dir)
            self._set_mode("bulk", clear_other=False)
        elif scenario:
            self._scenario_path.set_value(scenario)
            self._set_mode("single", clear_other=False)
        elif scenarios_dir:
            self._scenarios_dir.set_value(scenarios_dir)
            self._set_mode("bulk", clear_other=False)
        
        report = settings_service.load_last_report()
        if report:
            self._report_path.set_value(report)

        if settings_service.load_action_logging_enabled():
            self._action_logging_cb.setChecked(True)
        
        if settings_service.load_timing_logging_enabled():
            self._timing_logging_cb.setChecked(True)
        
        app = settings_service.load_last_app()
        if app:
            self._app_path.set_value(app)

        self._invalidate_validation()
        self._update_action_logging_env()
        self._update_timing_logging_env()
        self._update_preview()
    
    def save_last_paths(self, settings_service) -> None:
        """Save current paths to settings."""
        elements = self._elements_path.value()
        if elements:
            settings_service.save_last_elements(elements)
        
        scenario = self._scenario_path.value()
        if scenario:
            settings_service.save_last_scenario(scenario)

        scenarios_dir = self._scenarios_dir.value()
        if scenarios_dir:
            settings_service.save_last_scenarios_dir(scenarios_dir)

        settings_service.save_last_scenario_mode(self._mode)
        
        report = self._report_path.value()
        if report:
            settings_service.save_last_report(report)
        
        settings_service.save_action_logging_enabled(self._action_logging_cb.isChecked())
        settings_service.save_timing_logging_enabled(self._timing_logging_cb.isChecked())
        
        app = self._app_path.value()
        if app:
            settings_service.save_last_app(app)

    # -------------------------------------------------------------------------
    # Validation state management
    # -------------------------------------------------------------------------

    def _set_validation_state(self, state: str) -> None:
        """Set validation status and update run button."""
        self._validation_state = state
        if state == "validated":
            self._validation_status.setText("Validated ✅")
            self._validation_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
        elif state == "failed":
            self._validation_status.setText("Validation failed ❌")
            self._validation_status.setStyleSheet("color: #c62828; font-weight: bold;")
        elif state == "validating":
            self._validation_status.setText("Validating...")
            self._validation_status.setStyleSheet("color: #1565c0; font-weight: bold;")
        else:
            self._validation_status.setText("Needs validation")
            self._validation_status.setStyleSheet("color: #6d4c41; font-weight: bold;")

        self._update_run_enabled()

    def _invalidate_validation(self) -> None:
        if self._validation_state != "needs_validation":
            self._set_validation_state("needs_validation")
        else:
            self._update_run_enabled()

    def _update_run_enabled(self) -> None:
        should_enable = (not self._is_running) and self._validation_state == "validated"
        if hasattr(self, "_run_btn"):
            self._run_btn.setEnabled(should_enable)

    def _on_inputs_changed(self) -> None:
        self._invalidate_validation()
        self._update_action_logging_env()
        self._update_timing_logging_env()
        self._update_preview()
        self.values_changed.emit()

    def _on_action_logging_toggled(self) -> None:
        self._update_action_logging_env()

    def _update_action_logging_env(self) -> None:
        if not hasattr(self, "_action_logging_cb"):
            return
        if self._action_logging_cb.isChecked():
            os.environ["UIAUTO_ACTION_LOGGING"] = "1"
            report_path = self._report_path.value() if hasattr(self, "_report_path") else ""
            if report_path:
                report_path = str(Path(report_path))
                os.environ["UIAUTO_ACTION_LOG_FILE"] = f"{report_path}.actions.log"
            else:
                os.environ["UIAUTO_ACTION_LOG_FILE"] = "actions.log"
        else:
            os.environ.pop("UIAUTO_ACTION_LOGGING", None)
            os.environ.pop("UIAUTO_ACTION_LOG_FILE", None)

    def _on_timing_logging_toggled(self) -> None:
        self._update_timing_logging_env()

    def _update_timing_logging_env(self) -> None:
        if not hasattr(self, "_timing_logging_cb"):
            return
        if self._timing_logging_cb.isChecked():
            os.environ["UIAUTO_TIMING_LOGGING"] = "1"
            report_path = self._report_path.value() if hasattr(self, "_report_path") else ""
            if report_path:
                report_path = str(Path(report_path))
                os.environ["UIAUTO_TIMING_LOG_FILE"] = f"{report_path}.timing.log"
            else:
                os.environ["UIAUTO_TIMING_LOG_FILE"] = "timing.log"
        else:
            os.environ.pop("UIAUTO_TIMING_LOGGING", None)
            os.environ.pop("UIAUTO_TIMING_LOG_FILE", None)

    def _on_scenario_path_changed(self, text: str) -> None:
        if self._updating_mode:
            return
        if text.strip():
            self._set_mode("single", clear_other=True)
        self._on_inputs_changed()

    def _on_scenarios_dir_changed(self, text: str) -> None:
        if self._updating_mode:
            return
        if text.strip():
            self._set_mode("bulk", clear_other=True)
        self._on_inputs_changed()

    def _on_mode_toggled(self) -> None:
        if self._updating_mode:
            return
        if self._single_mode_rb.isChecked():
            self._set_mode("single", clear_other=True)
        elif self._bulk_mode_rb.isChecked():
            self._set_mode("bulk", clear_other=True)

    def _set_mode(self, mode: str, clear_other: bool = True) -> None:
        if mode not in ("single", "bulk"):
            return
        self._updating_mode = True
        try:
            self._mode = mode
            if mode == "single":
                self._single_mode_rb.setChecked(True)
                self._scenario_path.set_enabled(True)
                self._scenarios_dir.set_enabled(False)
                if clear_other:
                    self._scenarios_dir.clear()
            else:
                self._bulk_mode_rb.setChecked(True)
                self._scenario_path.set_enabled(False)
                self._scenarios_dir.set_enabled(True)
                if clear_other:
                    self._scenario_path.clear()
        finally:
            self._updating_mode = False
        self._invalidate_validation()

    # -------------------------------------------------------------------------
    # Command execution hooks
    # -------------------------------------------------------------------------

    def _on_validate_clicked(self) -> None:
        """Handle validate button click (CLI validate)."""
        result = self.validate()

        if not result.is_valid:
            QMessageBox.warning(
                self,
                "Validation Error",
                result.error_message
            )
            self._set_validation_state("failed")
            return

        if result.warnings:
            response = QMessageBox.warning(
                self,
                "Warnings",
                f"{result.all_messages}\n\nContinue anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if response != QMessageBox.Yes:
                return

        argv = self.build_validate_argv()
        if argv:
            self._set_validation_state("validating")
            self.command_requested.emit(argv)

    def build_validate_argv(self) -> list:
        """Build CLI argv for validate command."""
        from ..commands import ArgBuilder, get_command

        values = self._collect_validate_values()
        command_spec = get_command("validate")
        builder = ArgBuilder(command_spec)
        for name, value in values.items():
            builder.set(name, value)
        return builder.build()

    def handle_command_result(self, result) -> None:
        """Handle execution result to update validation state."""
        if result.command != "validate":
            return
        if result.success:
            self._set_validation_state("validated")
        else:
            self._set_validation_state("failed")

    def set_running(self, is_running: bool) -> None:
        """Override to keep run disabled until validated."""
        super().set_running(is_running)
        self._update_run_enabled()