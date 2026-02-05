# uiauto_ui/forms/inspect_form.py
"""
Form for 'uiauto inspect' command.
Inspects desktop UI and generates element maps.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QCheckBox, QSpinBox, QLineEdit,
    QPushButton, QLabel
)
from PySide6.QtCore import Signal

from .base_form import BaseCommandForm
from ..widgets.path_selector import PathSelector


class InspectForm(BaseCommandForm):
    """
    Form for the 'inspect' command.
    
    Collects:
    - Basic: window title filter, output directory, query
    - Generate: emit yaml options
    - Advanced: max controls, visibility flags
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
    
    def _get_command_name(self) -> str:
        return "inspect"
    
    def _build_form(self) -> None:
        """Build the inspect form UI."""
        
        # === Target Window Section ===
        target_group, target_layout = self._create_group("Target Window")
        
        self._window_title_re = QLineEdit()
        self._window_title_re.setPlaceholderText(
            "e.g., QtQuickTaskApp.* (leave empty for first visible)"
        )
        self._window_title_re.setToolTip(
            "Regular expression to match window title"
        )
        self._window_title_re.textChanged.connect(self._update_preview)
        self._register_widget("window-title-re", self._window_title_re)
        target_layout.addRow("Title (regex):", self._window_title_re)
        
        self._main_layout.addWidget(target_group)
        
        # === Output Section ===
        output_group, output_layout = self._create_group("Output")
        
        self._out_dir = PathSelector(
            mode="dir",
            placeholder="Output directory for reports"
        )
        self._out_dir.set_value("reports")
        self._out_dir.path_changed.connect(self._update_preview)
        self._register_widget("out", self._out_dir)
        output_layout.addRow("Directory:", self._out_dir)
        
        self._query = QLineEdit()
        self._query.setPlaceholderText("Filter by name, control_type, etc.")
        self._query.setToolTip(
            "Filter controls by text; use 'regex:<pattern>' for regex"
        )
        self._query.textChanged.connect(self._update_preview)
        self._register_widget("query", self._query)
        output_layout.addRow("Query:", self._query)
        
        self._main_layout.addWidget(output_group)
        
        # === Generate Object Map Section ===
        gen_group, gen_layout = self._create_group("Generate Object Map")
        
        self._emit_yaml_cb = QCheckBox("Generate elements.yaml")
        self._emit_yaml_cb.setChecked(True)
        self._emit_yaml_cb.stateChanged.connect(self._on_emit_yaml_changed)
        self._emit_yaml_cb.stateChanged.connect(self._update_preview)
        self._register_widget("emit_yaml_enabled", self._emit_yaml_cb)
        gen_layout.addRow("", self._emit_yaml_cb)
        
        self._emit_yaml_path = PathSelector(
            mode="save",
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
            placeholder="Output path for generated elements.yaml"
        )
        self._emit_yaml_path.path_changed.connect(self._update_preview)
        self._register_widget("emit-elements-yaml", self._emit_yaml_path)
        gen_layout.addRow("Output Path:", self._emit_yaml_path)
        
        # Window name and state
        name_state_layout = QHBoxLayout()
        
        name_state_layout.addWidget(QLabel("Window:"))
        self._emit_window_name = QLineEdit("main")
        self._emit_window_name.setMaximumWidth(100)
        self._emit_window_name.setToolTip("Window name in generated YAML")
        self._emit_window_name.textChanged.connect(self._update_preview)
        self._register_widget("emit-window-name", self._emit_window_name)
        name_state_layout.addWidget(self._emit_window_name)
        
        name_state_layout.addWidget(QLabel("State:"))
        self._state = QLineEdit("default")
        self._state.setMaximumWidth(100)
        self._state.setToolTip("UI state name in generated YAML")
        self._state.textChanged.connect(self._update_preview)
        self._register_widget("state", self._state)
        name_state_layout.addWidget(self._state)
        
        name_state_layout.addStretch()
        gen_layout.addRow("", name_state_layout)
        
        self._merge_cb = QCheckBox("Merge with existing file")
        self._merge_cb.setToolTip("Merge new elements into existing file")
        self._merge_cb.stateChanged.connect(self._update_preview)
        self._register_widget("merge", self._merge_cb)
        gen_layout.addRow("", self._merge_cb)
        
        self._main_layout.addWidget(gen_group)
        
        # === Advanced Section (Collapsible) ===
        advanced_group, advanced_layout = self._create_collapsible_group(
            "Advanced Settings",
            collapsed=True
        )
        
        self._max_controls = QSpinBox()
        self._max_controls.setRange(100, 10000)
        self._max_controls.setValue(3000)
        self._max_controls.setSingleStep(500)
        self._max_controls.setToolTip("Maximum number of controls to scan")
        self._max_controls.valueChanged.connect(self._update_preview)
        self._register_widget("max-controls", self._max_controls)
        advanced_layout.addRow("Max Controls:", self._max_controls)
        
        # Visibility flags
        flags_layout = QHBoxLayout()
        
        self._include_invisible = QCheckBox("Include invisible")
        self._include_invisible.setToolTip("Include invisible controls in output")
        self._include_invisible.stateChanged.connect(self._update_preview)
        self._register_widget("include-invisible", self._include_invisible)
        flags_layout.addWidget(self._include_invisible)
        
        self._exclude_disabled = QCheckBox("Exclude disabled")
        self._exclude_disabled.setToolTip("Exclude disabled controls from output")
        self._exclude_disabled.stateChanged.connect(self._update_preview)
        self._register_widget("exclude-disabled", self._exclude_disabled)
        flags_layout.addWidget(self._exclude_disabled)
        
        flags_layout.addStretch()
        advanced_layout.addRow("", flags_layout)
        
        self._main_layout.addWidget(advanced_group)
    
    def _on_emit_yaml_changed(self, state: int) -> None:
        """Handle emit yaml checkbox change."""
        from PySide6.QtCore import Qt
        enabled = (state == Qt.Checked)
        self._emit_yaml_path.setEnabled(enabled)
        self._emit_window_name.setEnabled(enabled)
        self._state.setEnabled(enabled)
        self._merge_cb.setEnabled(enabled)
    
    def _create_run_button(self) -> QPushButton:
        """Create inspect button with blue styling."""
        btn = QPushButton("Inspect Now")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 24px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #9E9E9E;
            }
        """)
        return btn
    
    def _collect_values(self) -> Dict[str, Any]:
        """Collect all form values."""
        values = {
            "window-title-re": self._window_title_re.text().strip(),
            "out": self._out_dir.value(),
            "query": self._query.text().strip(),
            "max-controls": self._max_controls.value(),
            "include-invisible": self._include_invisible.isChecked(),
            "exclude-disabled": self._exclude_disabled.isChecked(),
        }
        
        # Only include emit-yaml options if enabled
        if self._emit_yaml_cb.isChecked():
            emit_path = self._emit_yaml_path.value()
            if emit_path:
                values["emit-elements-yaml"] = emit_path
                
                window_name = self._emit_window_name.text().strip()
                if window_name and window_name != "main":
                    values["emit-window-name"] = window_name
                
                state = self._state.text().strip()
                if state and state != "default":
                    values["state"] = state
                
                if self._merge_cb.isChecked():
                    values["merge"] = True
        
        return values
    
    def set_values(self, values: Dict[str, Any]) -> None:
        """Populate form from values dictionary."""
        if "window-title-re" in values:
            self._window_title_re.setText(values["window-title-re"])
        if "out" in values:
            self._out_dir.set_value(values["out"])
        if "query" in values:
            self._query.setText(values["query"])
        if "max-controls" in values:
            self._max_controls.setValue(values["max-controls"])
        if "include-invisible" in values:
            self._include_invisible.setChecked(values["include-invisible"])
        if "exclude-disabled" in values:
            self._exclude_disabled.setChecked(values["exclude-disabled"])
        if "emit-elements-yaml" in values:
            self._emit_yaml_cb.setChecked(True)
            self._emit_yaml_path.set_value(values["emit-elements-yaml"])
        if "emit-window-name" in values:
            self._emit_window_name.setText(values["emit-window-name"])
        if "state" in values:
            self._state.setText(values["state"])
        if "merge" in values:
            self._merge_cb.setChecked(values["merge"])
        
        self._update_preview()
    
    def reset(self) -> None:
        """Reset form to defaults."""
        self._window_title_re.clear()
        self._out_dir.set_value("reports")
        self._query.clear()
        self._max_controls.setValue(3000)
        self._include_invisible.setChecked(False)
        self._exclude_disabled.setChecked(False)
        self._emit_yaml_cb.setChecked(True)
        self._emit_yaml_path.clear()
        self._emit_window_name.setText("main")
        self._state.setText("default")
        self._merge_cb.setChecked(False)
        self._update_preview()