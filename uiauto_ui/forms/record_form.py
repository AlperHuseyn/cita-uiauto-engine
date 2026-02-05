# uiauto_ui/forms/record_form.py
"""
Form for 'uiauto record' command.
Records user interactions into YAML scenarios.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QLabel
)
from PySide6.QtCore import Signal

from .base_form import BaseCommandForm
from ..widgets.path_selector import PathSelector


class RecordForm(BaseCommandForm):
    """
    Form for the 'record' command.
    
    Collects:
    - Required: elements.yaml, scenario output path
    - Optional: window title filter
    - Advanced: window name, state, debug JSON
    
    Special behavior:
    - Uses subprocess executor (not in-process)
    - Has Start/Stop buttons instead of single Run
    """
    
    # Additional signals for record-specific behavior
    stop_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        self._is_recording = False
        super().__init__(parent)
    
    def _get_command_name(self) -> str:
        return "record"
    
    def _build_form(self) -> None:
        """Build the record form UI."""
        
        # === Required Section ===
        required_group, required_layout = self._create_group("Required")
        
        self._elements_path = PathSelector(
            mode="file",
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
            placeholder="Path to elements.yaml (will be updated)"
        )
        self._elements_path.path_changed.connect(self._update_preview)
        self._register_widget("elements", self._elements_path)
        required_layout.addRow("Elements:", self._elements_path)
        
        self._scenario_out = PathSelector(
            mode="save",
            file_filter="YAML Files (*.yaml *.yml);;All Files (*)",
            placeholder="Output path for recorded scenario"
        )
        self._scenario_out.path_changed.connect(self._update_preview)
        self._register_widget("scenario-out", self._scenario_out)
        required_layout.addRow("Scenario Out:", self._scenario_out)
        
        self._main_layout.addWidget(required_group)
        
        # === Filtering Section ===
        filter_group, filter_layout = self._create_group("Filtering")
        
        self._window_title_re = QLineEdit()
        self._window_title_re.setPlaceholderText(
            "Limit recording to matching window (optional)"
        )
        self._window_title_re.setToolTip(
            "Regular expression to match window title for recording"
        )
        self._window_title_re.textChanged.connect(self._update_preview)
        self._register_widget("window-title-re", self._window_title_re)
        filter_layout.addRow("Title (regex):", self._window_title_re)
        
        self._main_layout.addWidget(filter_group)
        
        # === Advanced Section (Collapsible) ===
        advanced_group, advanced_layout = self._create_collapsible_group(
            "Advanced Settings",
            collapsed=True
        )
        
        # Window name and state
        name_state_layout = QHBoxLayout()
        
        name_state_layout.addWidget(QLabel("Window:"))
        self._window_name = QLineEdit("main")
        self._window_name.setMaximumWidth(100)
        self._window_name.setToolTip("Window name for recorded elements")
        self._window_name.textChanged.connect(self._update_preview)
        self._register_widget("window-name", self._window_name)
        name_state_layout.addWidget(self._window_name)
        
        name_state_layout.addWidget(QLabel("State:"))
        self._state = QLineEdit("default")
        self._state.setMaximumWidth(100)
        self._state.setToolTip("UI state name for recorded elements")
        self._state.textChanged.connect(self._update_preview)
        self._register_widget("state", self._state)
        name_state_layout.addWidget(self._state)
        
        name_state_layout.addStretch()
        advanced_layout.addRow("", name_state_layout)
        
        self._debug_json = PathSelector(
            mode="save",
            file_filter="JSON Files (*.json);;All Files (*)",
            placeholder="Optional: debug snapshots output"
        )
        self._debug_json.path_changed.connect(self._update_preview)
        self._register_widget("debug-json-out", self._debug_json)
        advanced_layout.addRow("Debug JSON:", self._debug_json)
        
        self._main_layout.addWidget(advanced_group)
        
        # === Recording Info Box ===
        self._build_info_section()
    
    def _build_info_section(self) -> None:
        """Build the recording info section."""
        info_group = QGroupBox("Recording Info")
        info_layout = QVBoxLayout(info_group)
        
        info_label = QLabel(
            "Recording will capture:\n"
            "  • Mouse clicks on UI elements\n"
            "  • Keyboard typing and text input\n"
            "  • Hotkeys (Ctrl+S, Alt+F4, etc.)\n\n"
            "Press <b>Ctrl+Alt+Q</b> to stop recording"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                padding: 12px;
                border-radius: 4px;
                color: #1565C0;
            }
        """)
        info_layout.addWidget(info_label)
        
        self._main_layout.addWidget(info_group)
    
    def _build_button_section(self) -> None:
        """Build custom button section for record form."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # Validate button
        self._validate_btn = QPushButton("Validate")
        self._validate_btn.setToolTip("Validate form inputs")
        self._validate_btn.clicked.connect(self._on_validate_clicked)
        btn_layout.addWidget(self._validate_btn)
        
        # Start Recording button
        self._run_btn = QPushButton("Start Recording")
        self._run_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                font-weight: bold;
                padding: 8px 24px;
                border-radius: 4px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
            QPushButton:disabled {
                background-color: #9E9E9E;
            }
        """)
        self._run_btn.clicked.connect(self._on_run_clicked)
        btn_layout.addWidget(self._run_btn)
        
        # Stop button
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        btn_layout.addWidget(self._stop_btn)
        
        self._main_layout.addLayout(btn_layout)
    
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.stop_requested.emit()
    
    def _collect_values(self) -> Dict[str, Any]:
        """Collect all form values."""
        values = {
            "elements": self._elements_path.value(),
            "scenario-out": self._scenario_out.value(),
            "window-title-re": self._window_title_re.text().strip(),
        }
        
        window_name = self._window_name.text().strip()
        if window_name and window_name != "main":
            values["window-name"] = window_name
        
        state = self._state.text().strip()
        if state and state != "default":
            values["state"] = state
        
        debug_json = self._debug_json.value()
        if debug_json:
            values["debug-json-out"] = debug_json
        
        return values
    
    def set_values(self, values: Dict[str, Any]) -> None:
        """Populate form from values dictionary."""
        if "elements" in values:
            self._elements_path.set_value(values["elements"])
        if "scenario-out" in values:
            self._scenario_out.set_value(values["scenario-out"])
        if "window-title-re" in values:
            self._window_title_re.setText(values["window-title-re"])
        if "window-name" in values:
            self._window_name.setText(values["window-name"])
        if "state" in values:
            self._state.setText(values["state"])
        if "debug-json-out" in values:
            self._debug_json.set_value(values["debug-json-out"])
        
        self._update_preview()
    
    def reset(self) -> None:
        """Reset form to defaults."""
        self._elements_path.clear()
        self._scenario_out.clear()
        self._window_title_re.clear()
        self._window_name.setText("main")
        self._state.setText("default")
        self._debug_json.clear()
        self._update_preview()
    
    # -------------------------------------------------------------------------
    # Recording State Management
    # -------------------------------------------------------------------------
    
    def set_recording(self, is_recording: bool) -> None:
        """
        Set recording state.
        
        Args:
            is_recording: True if recording is in progress
        """
        self._is_recording = is_recording
        
        # Update button states
        self._run_btn.setEnabled(not is_recording)
        self._stop_btn.setEnabled(is_recording)
        self._validate_btn.setEnabled(not is_recording)
        
        # Update button text
        if is_recording:
            self._run_btn.setText("Recording...")
        else:
            self._run_btn.setText("Start Recording")
        
        # Disable/enable input widgets
        for widget in self._widgets.values():
            if hasattr(widget, 'setEnabled'):
                widget.setEnabled(not is_recording)
    
    def set_running(self, is_running: bool) -> None:
        """Override to use recording-specific behavior."""
        self.set_recording(is_running)
    
    @property
    def is_recording(self) -> bool:
        """True if currently recording."""
        return self._is_recording