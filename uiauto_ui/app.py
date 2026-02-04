# uiauto_ui/app.py
"""
Minimal PySide6 UI for cita-uiauto-engine CLI.
"""

import sys
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QTextEdit, QGroupBox, QFormLayout, QCheckBox, QDoubleSpinBox,
    QSpinBox, QMessageBox, QSplitter, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal, QProcess
from PySide6.QtGui import QFont, QColor


# =============================================================================
# Command Specifications (CLI ile birebir eşleşme)
# =============================================================================

class ArgType(Enum):
    PATH = "path"
    SAVE_PATH = "save_path"
    DIR_PATH = "dir_path"
    STRING = "string"
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    KEY_VALUE_LIST = "key_value_list"


@dataclass
class ArgSpec:
    name: str
    short: Optional[str] = None
    arg_type: ArgType = ArgType.STRING
    required: bool = False
    default: any = None
    help_text: str = ""
    category: str = "basic"


# =============================================================================
# CLI Executor
# =============================================================================

class CLIExecutor(QThread):
    """Runs CLI commands in a background thread."""
    
    output_received = Signal(str)
    finished_with_code = Signal(int)
    
    def __init__(self, argv: list):
        super().__init__()
        self.argv = argv
        self._process: Optional[QProcess] = None
    
    def run(self):
        """Execute CLI in the same process (for run/inspect)."""
        import io
        import contextlib
        
        # Redirect stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            # Import here to avoid circular imports
            from uiauto.cli import main
            
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                return_code = main(self.argv)
            
            output = stdout_capture.getvalue()
            errors = stderr_capture.getvalue()
            
            if output:
                self.output_received.emit(output)
            if errors:
                self.output_received.emit(f"[STDERR]\n{errors}")
            
            self.finished_with_code.emit(return_code)
            
        except Exception as e:
            self.output_received.emit(f"[ERROR] {type(e).__name__}: {e}")
            self.finished_with_code.emit(1)


class SubprocessExecutor(QThread):
    """Runs CLI as subprocess (for record command)."""
    
    output_received = Signal(str)
    finished_with_code = Signal(int)
    
    def __init__(self, argv: list):
        super().__init__()
        self.argv = argv
        self._should_stop = False
        self._process = None
    
    def run(self):
        import subprocess
        
        cmd = [sys.executable, "-m", "uiauto.cli"] + self.argv
        
        # Set environment for UTF-8 encoding
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",  # Replace undecodable chars instead of failing
                env=env
            )
            
            for line in iter(self._process.stdout.readline, ''):
                if self._should_stop:
                    self._process.terminate()
                    break
                self.output_received.emit(line.rstrip())
            
            self._process.wait()
            self.finished_with_code.emit(self._process.returncode)
            
        except Exception as e:
            self.output_received.emit(f"[ERROR] {type(e).__name__}: {e}")
            self.finished_with_code.emit(1)
    
    def stop(self):
        self._should_stop = True
        if self._process:
            try:
                self._process.terminate()
            except:
                pass


# =============================================================================
# Reusable Widgets
# =============================================================================

class PathSelector(QWidget):
    """File/directory path selector with browse button."""
    
    def __init__(
        self, 
        label: str = "",
        mode: str = "file",  # file | save | dir
        filter: str = "All Files (*)",
        parent=None
    ):
        super().__init__(parent)
        self.mode = mode
        self.filter = filter
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(f"Select {mode}...")
        layout.addWidget(self.line_edit, stretch=1)
        
        self.browse_btn = QPushButton("...")
        self.browse_btn.setFixedWidth(30)
        self.browse_btn.clicked.connect(self._browse)
        layout.addWidget(self.browse_btn)
    
    def _browse(self):
        if self.mode == "file":
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", "", self.filter
            )
        elif self.mode == "save":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save File", "", self.filter
            )
        elif self.mode == "dir":
            path = QFileDialog.getExistingDirectory(
                self, "Select Directory"
            )
        else:
            path = ""
        
        if path:
            self.line_edit.setText(path)
    
    def value(self) -> str:
        return self.line_edit.text().strip()
    
    def set_value(self, value: str):
        self.line_edit.setText(value)


class KeyValueTable(QWidget):
    """Table for key=value pairs (for --var arguments)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(80)
        self.table.setMaximumHeight(120)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("+")
        add_btn.setFixedWidth(30)
        add_btn.clicked.connect(self._add_row)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("-")
        remove_btn.setFixedWidth(30)
        remove_btn.clicked.connect(self._remove_row)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
    
    def _remove_row(self):
        current = self.table.currentRow()
        if current >= 0:
            self.table.removeRow(current)
    
    def values(self) -> list:
        """Returns list of 'KEY=VALUE' strings."""
        result = []
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            val_item = self.table.item(row, 1)
            if key_item and val_item:
                key = key_item.text().strip()
                val = val_item.text().strip()
                if key:
                    result.append(f"{key}={val}")
        return result


# =============================================================================
# Form Base Class
# =============================================================================

class BaseCommandForm(QWidget):
    """Base class for command forms."""
    
    command_ready = Signal(list)  # Emits argv when ready to run
    
    def __init__(self, command_name: str, parent=None):
        super().__init__(parent)
        self.command_name = command_name
        self._build_ui()
    
    def _build_ui(self):
        """Override in subclasses."""
        raise NotImplementedError
    
    def build_argv(self) -> list:
        """Build CLI argv from form values. Override in subclasses."""
        raise NotImplementedError
    
    def validate(self) -> tuple:
        """Validate form. Returns (is_valid, error_message)."""
        return True, ""
    
    def format_command_preview(self, argv: list) -> str:
        """Format argv as multi-line command for readability."""
        if not argv:
            return "(incomplete)"
        
        lines = ["python -m uiauto.cli \\"]
        lines.append(f"    {argv[0]} \\")  # command name
        
        i = 1
        while i < len(argv):
            arg = argv[i]
            if arg.startswith("--"):
                # Check if next item is a value
                if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                    lines.append(f"    {arg} \"{argv[i + 1]}\" \\")
                    i += 2
                else:
                    lines.append(f"    {arg} \\")
                    i += 1
            else:
                lines.append(f"    \"{arg}\" \\")
                i += 1
        
        # Remove trailing backslash from last line
        if lines:
            lines[-1] = lines[-1].rstrip(" \\")
        
        return "\n".join(lines)


# =============================================================================
# Run Form
# =============================================================================

class RunForm(BaseCommandForm):
    """Form for 'uiauto run' command."""
    
    def __init__(self, parent=None):
        super().__init__("run", parent)
    
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # === Required Section ===
        required_group = QGroupBox("Required")
        required_layout = QFormLayout(required_group)
        required_layout.setSpacing(5)
        
        self.elements_path = PathSelector(
            mode="file", 
            filter="YAML Files (*.yaml *.yml);;All Files (*)"
        )
        required_layout.addRow("Elements:", self.elements_path)
        
        self.scenario_path = PathSelector(
            mode="file",
            filter="YAML Files (*.yaml *.yml);;All Files (*)"
        )
        required_layout.addRow("Scenario:", self.scenario_path)
        
        main_layout.addWidget(required_group)
        
        # === Options Section ===
        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)
        options_layout.setSpacing(5)
        
        self.app_path = PathSelector(
            mode="file",
            filter="Executables (*.exe);;All Files (*)"
        )
        options_layout.addRow("App Path:", self.app_path)
        
        self.report_path = PathSelector(mode="save", filter="JSON Files (*.json)")
        self.report_path.set_value("report.json")
        options_layout.addRow("Report:", self.report_path)
        
        self.verbose_cb = QCheckBox("Verbose output")
        options_layout.addRow("", self.verbose_cb)
        
        main_layout.addWidget(options_group)
        
        # === Advanced Section (Collapsible) ===
        advanced_group = QGroupBox("Advanced Settings")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)
        advanced_layout = QFormLayout(advanced_group)
        advanced_layout.setSpacing(5)
        
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0, 300)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setSpecialValueText("Default")
        self.timeout_spin.setValue(0)
        advanced_layout.addRow("Timeout (s):", self.timeout_spin)
        
        mode_layout = QHBoxLayout()
        self.ci_cb = QCheckBox("CI Mode")
        self.fast_cb = QCheckBox("Fast Mode")
        mode_layout.addWidget(self.ci_cb)
        mode_layout.addWidget(self.fast_cb)
        mode_layout.addStretch()
        advanced_layout.addRow("", mode_layout)
        
        self.schema_path = PathSelector(mode="file", filter="JSON Files (*.json)")
        advanced_layout.addRow("Schema:", self.schema_path)
        
        self.vars_path = PathSelector(mode="file", filter="JSON Files (*.json)")
        advanced_layout.addRow("Vars File:", self.vars_path)
        
        self.var_table = KeyValueTable()
        advanced_layout.addRow("Inline Vars:", self.var_table)
        
        main_layout.addWidget(advanced_group)
        
        # === Command Preview ===
        preview_group = QGroupBox("Generated Command")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(100)
        self.command_preview.setFont(QFont("Consolas", 9))
        self.command_preview.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        preview_layout.addWidget(self.command_preview)
        main_layout.addWidget(preview_group)
        
        # === Buttons ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self._validate_files)
        btn_layout.addWidget(validate_btn)
        
        run_btn = QPushButton("Run")
        run_btn.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                padding: 8px 20px; 
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        run_btn.clicked.connect(self._run)
        btn_layout.addWidget(run_btn)
        
        main_layout.addLayout(btn_layout)
        main_layout.addStretch()
        
        # Connect signals for live preview
        self.elements_path.line_edit.textChanged.connect(self._update_preview)
        self.scenario_path.line_edit.textChanged.connect(self._update_preview)
        self.app_path.line_edit.textChanged.connect(self._update_preview)
        self.report_path.line_edit.textChanged.connect(self._update_preview)
        self.verbose_cb.stateChanged.connect(self._update_preview)
        self.timeout_spin.valueChanged.connect(self._update_preview)
        self.ci_cb.stateChanged.connect(self._update_preview)
        self.fast_cb.stateChanged.connect(self._update_preview)
    
    def _update_preview(self):
        try:
            argv = self.build_argv()
            self.command_preview.setText(self.format_command_preview(argv))
        except:
            self.command_preview.setText("(incomplete)")
    
    def build_argv(self) -> list:
        argv = ["run"]
        
        elements = self.elements_path.value()
        if elements:
            argv.extend(["--elements", elements])
        
        scenario = self.scenario_path.value()
        if scenario:
            argv.extend(["--scenario", scenario])
        
        app = self.app_path.value()
        if app:
            argv.extend(["--app", app])
        
        report = self.report_path.value()
        if report:
            argv.extend(["--report", report])
        
        if self.verbose_cb.isChecked():
            argv.append("--verbose")
        
        timeout = self.timeout_spin.value()
        if timeout > 0:
            argv.extend(["--timeout", str(timeout)])
        
        if self.ci_cb.isChecked():
            argv.append("--ci")
        
        if self.fast_cb.isChecked():
            argv.append("--fast")
        
        schema = self.schema_path.value()
        if schema:
            argv.extend(["--schema", schema])
        
        vars_file = self.vars_path.value()
        if vars_file:
            argv.extend(["--vars", vars_file])
        
        for var in self.var_table.values():
            argv.extend(["--var", var])
        
        return argv
    
    def validate(self) -> tuple:
        elements = self.elements_path.value()
        if not elements:
            return False, "Elements file is required"
        if not os.path.exists(elements):
            return False, f"Elements file not found: {elements}"
        
        scenario = self.scenario_path.value()
        if not scenario:
            return False, "Scenario file is required"
        if not os.path.exists(scenario):
            return False, f"Scenario file not found: {scenario}"
        
        return True, ""
    
    def _validate_files(self):
        is_valid, error = self.validate()
        if is_valid:
            QMessageBox.information(self, "Validation", "All files are valid!")
        else:
            QMessageBox.warning(self, "Validation Error", error)
    
    def _run(self):
        is_valid, error = self.validate()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error)
            return
        
        argv = self.build_argv()
        self.command_ready.emit(argv)


# =============================================================================
# Inspect Form
# =============================================================================

class InspectForm(BaseCommandForm):
    """Form for 'uiauto inspect' command."""
    
    def __init__(self, parent=None):
        super().__init__("inspect", parent)
    
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # === Target Window ===
        target_group = QGroupBox("Target Window")
        target_layout = QFormLayout(target_group)
        target_layout.setSpacing(5)
        
        self.window_title_re = QLineEdit()
        self.window_title_re.setPlaceholderText("e.g., QtQuickTaskApp.* (leave empty for first visible)")
        target_layout.addRow("Title (regex):", self.window_title_re)
        
        main_layout.addWidget(target_group)
        
        # === Output ===
        output_group = QGroupBox("Output")
        output_layout = QFormLayout(output_group)
        output_layout.setSpacing(5)
        
        self.out_dir = PathSelector(mode="dir")
        self.out_dir.set_value("reports")
        output_layout.addRow("Directory:", self.out_dir)
        
        self.query = QLineEdit()
        self.query.setPlaceholderText("Filter by name, control_type, etc.")
        output_layout.addRow("Query:", self.query)
        
        main_layout.addWidget(output_group)
        
        # === Generate Object Map ===
        gen_group = QGroupBox("Generate Object Map")
        gen_layout = QFormLayout(gen_group)
        gen_layout.setSpacing(5)
        
        self.emit_yaml_cb = QCheckBox("Generate elements.yaml")
        self.emit_yaml_cb.setChecked(True)
        gen_layout.addRow("", self.emit_yaml_cb)
        
        self.emit_yaml_path = PathSelector(mode="save", filter="YAML Files (*.yaml)")
        gen_layout.addRow("Output Path:", self.emit_yaml_path)
        
        name_state_layout = QHBoxLayout()
        self.emit_window_name = QLineEdit("main")
        self.emit_window_name.setMaximumWidth(100)
        name_state_layout.addWidget(QLabel("Window:"))
        name_state_layout.addWidget(self.emit_window_name)
        self.state = QLineEdit("default")
        self.state.setMaximumWidth(100)
        name_state_layout.addWidget(QLabel("State:"))
        name_state_layout.addWidget(self.state)
        name_state_layout.addStretch()
        gen_layout.addRow("", name_state_layout)
        
        self.merge_cb = QCheckBox("Merge with existing file")
        gen_layout.addRow("", self.merge_cb)
        
        main_layout.addWidget(gen_group)
        
        # === Advanced ===
        advanced_group = QGroupBox("Advanced Settings")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)
        advanced_layout = QFormLayout(advanced_group)
        advanced_layout.setSpacing(5)
        
        self.max_controls = QSpinBox()
        self.max_controls.setRange(100, 10000)
        self.max_controls.setValue(3000)
        advanced_layout.addRow("Max Controls:", self.max_controls)
        
        flags_layout = QHBoxLayout()
        self.include_invisible = QCheckBox("Include invisible")
        self.exclude_disabled = QCheckBox("Exclude disabled")
        flags_layout.addWidget(self.include_invisible)
        flags_layout.addWidget(self.exclude_disabled)
        flags_layout.addStretch()
        advanced_layout.addRow("", flags_layout)
        
        main_layout.addWidget(advanced_group)
        
        # === Command Preview ===
        preview_group = QGroupBox("Generated Command")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(100)
        self.command_preview.setFont(QFont("Consolas", 9))
        self.command_preview.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        preview_layout.addWidget(self.command_preview)
        main_layout.addWidget(preview_group)
        
        # === Buttons ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        run_btn = QPushButton("Inspect Now")
        run_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2196F3; 
                color: white; 
                font-weight: bold; 
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        run_btn.clicked.connect(self._run)
        btn_layout.addWidget(run_btn)
        
        main_layout.addLayout(btn_layout)
        main_layout.addStretch()
        
        # Connect for live preview
        self.window_title_re.textChanged.connect(self._update_preview)
        self.out_dir.line_edit.textChanged.connect(self._update_preview)
        self.emit_yaml_cb.stateChanged.connect(self._update_preview)
        self.emit_yaml_path.line_edit.textChanged.connect(self._update_preview)
    
    def _update_preview(self):
        try:
            argv = self.build_argv()
            self.command_preview.setText(self.format_command_preview(argv))
        except:
            self.command_preview.setText("(incomplete)")
    
    def build_argv(self) -> list:
        argv = ["inspect"]
        
        window_re = self.window_title_re.text().strip()
        if window_re:
            argv.extend(["--window-title-re", window_re])
        
        out_dir = self.out_dir.value()
        if out_dir:
            argv.extend(["--out", out_dir])
        
        query = self.query.text().strip()
        if query:
            argv.extend(["--query", query])
        
        argv.extend(["--max-controls", str(self.max_controls.value())])
        
        if self.include_invisible.isChecked():
            argv.append("--include-invisible")
        
        if self.exclude_disabled.isChecked():
            argv.append("--exclude-disabled")
        
        if self.emit_yaml_cb.isChecked():
            emit_path = self.emit_yaml_path.value()
            if emit_path:
                argv.extend(["--emit-elements-yaml", emit_path])
                
                window_name = self.emit_window_name.text().strip()
                if window_name and window_name != "main":
                    argv.extend(["--emit-window-name", window_name])
                
                state = self.state.text().strip()
                if state and state != "default":
                    argv.extend(["--state", state])
                
                if self.merge_cb.isChecked():
                    argv.append("--merge")
        
        return argv
    
    def _run(self):
        argv = self.build_argv()
        self.command_ready.emit(argv)


# =============================================================================
# Record Form
# =============================================================================

class RecordForm(BaseCommandForm):
    """Form for 'uiauto record' command."""
    
    def __init__(self, parent=None):
        super().__init__("record", parent)
        self._executor: Optional[SubprocessExecutor] = None
    
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # === Required ===
        required_group = QGroupBox("Required")
        required_layout = QFormLayout(required_group)
        required_layout.setSpacing(5)
        
        self.elements_path = PathSelector(
            mode="file",
            filter="YAML Files (*.yaml *.yml);;All Files (*)"
        )
        required_layout.addRow("Elements:", self.elements_path)
        
        self.scenario_out = PathSelector(
            mode="save",
            filter="YAML Files (*.yaml *.yml)"
        )
        required_layout.addRow("Scenario Out:", self.scenario_out)
        
        main_layout.addWidget(required_group)
        
        # === Filtering ===
        filter_group = QGroupBox("Filtering")
        filter_layout = QFormLayout(filter_group)
        filter_layout.setSpacing(5)
        
        self.window_title_re = QLineEdit()
        self.window_title_re.setPlaceholderText("Limit recording to matching window")
        filter_layout.addRow("Title (regex):", self.window_title_re)
        
        main_layout.addWidget(filter_group)
        
        # === Advanced ===
        advanced_group = QGroupBox("Advanced Settings")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)
        advanced_layout = QFormLayout(advanced_group)
        advanced_layout.setSpacing(5)
        
        name_state_layout = QHBoxLayout()
        self.window_name = QLineEdit("main")
        self.window_name.setMaximumWidth(100)
        name_state_layout.addWidget(QLabel("Window:"))
        name_state_layout.addWidget(self.window_name)
        self.state = QLineEdit("default")
        self.state.setMaximumWidth(100)
        name_state_layout.addWidget(QLabel("State:"))
        name_state_layout.addWidget(self.state)
        name_state_layout.addStretch()
        advanced_layout.addRow("", name_state_layout)
        
        self.debug_json = PathSelector(mode="save", filter="JSON Files (*.json)")
        advanced_layout.addRow("Debug JSON:", self.debug_json)
        
        main_layout.addWidget(advanced_group)
        
        # === Info ===
        info_group = QGroupBox("Recording Info")
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(
            "Recording will capture:\n"
            "  - Mouse clicks\n"
            "  - Keyboard typing\n"
            "  - Hotkeys (Ctrl+S, etc.)\n\n"
            "Press Ctrl+Alt+Q to stop recording"
        )
        info_label.setStyleSheet("""
            background-color: #E3F2FD; 
            padding: 10px; 
            border-radius: 4px;
            color: #1565C0;
        """)
        info_layout.addWidget(info_label)
        main_layout.addWidget(info_group)
        
        # === Command Preview ===
        preview_group = QGroupBox("Generated Command")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(100)
        self.command_preview.setFont(QFont("Consolas", 9))
        self.command_preview.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        preview_layout.addWidget(self.command_preview)
        main_layout.addWidget(preview_group)
        
        # === Buttons ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.start_btn = QPushButton("Start Recording")
        self.start_btn.setStyleSheet("""
            QPushButton { 
                background-color: #FF5722; 
                color: white; 
                font-weight: bold; 
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        self.start_btn.clicked.connect(self._start_recording)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton { 
                padding: 8px 20px;
                border-radius: 4px;
            }
        """)
        self.stop_btn.clicked.connect(self._stop_recording)
        btn_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(btn_layout)
        main_layout.addStretch()
        
        # Connect for live preview
        self.elements_path.line_edit.textChanged.connect(self._update_preview)
        self.scenario_out.line_edit.textChanged.connect(self._update_preview)
        self.window_title_re.textChanged.connect(self._update_preview)
    
    def _update_preview(self):
        try:
            argv = self.build_argv()
            self.command_preview.setText(self.format_command_preview(argv))
        except:
            self.command_preview.setText("(incomplete)")
    
    def build_argv(self) -> list:
        argv = ["record"]
        
        elements = self.elements_path.value()
        if elements:
            argv.extend(["--elements", elements])
        
        scenario_out = self.scenario_out.value()
        if scenario_out:
            argv.extend(["--scenario-out", scenario_out])
        
        window_re = self.window_title_re.text().strip()
        if window_re:
            argv.extend(["--window-title-re", window_re])
        
        window_name = self.window_name.text().strip()
        if window_name and window_name != "main":
            argv.extend(["--window-name", window_name])
        
        state = self.state.text().strip()
        if state and state != "default":
            argv.extend(["--state", state])
        
        debug_json = self.debug_json.value()
        if debug_json:
            argv.extend(["--debug-json-out", debug_json])
        
        return argv
    
    def validate(self) -> tuple:
        elements = self.elements_path.value()
        if not elements:
            return False, "Elements file is required"
        
        scenario_out = self.scenario_out.value()
        if not scenario_out:
            return False, "Scenario output path is required"
        
        return True, ""
    
    def _start_recording(self):
        is_valid, error = self.validate()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error)
            return
        
        argv = self.build_argv()
        self.command_ready.emit(argv)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def _stop_recording(self):
        # Recording is stopped via Ctrl+Alt+Q globally
        # This button is for UI feedback only
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)


# =============================================================================
# Output Viewer
# =============================================================================

class OutputViewer(QWidget):
    """Displays CLI output and status."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with status
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Output")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px;")
        header_layout.addWidget(self.status_label)
        
        self.duration_label = QLabel("")
        self.duration_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.duration_label)
        
        layout.addLayout(header_layout)
        
        # Output text
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.output_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy_output)
        btn_layout.addWidget(copy_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
    
    def append_output(self, text: str):
        self.output_text.append(text)
        # Auto-scroll to bottom
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def set_status(self, status: str, color: str = "black"):
        self.status_label.setText(status)
        
        # Set background color based on status
        if "PASSED" in status or "Complete" in status:
            bg_color = "#4CAF50"
            text_color = "white"
        elif "FAILED" in status or "Error" in status:
            bg_color = "#F44336"
            text_color = "white"
        elif "Running" in status or "Recording" in status:
            bg_color = "#FF9800"
            text_color = "white"
        else:
            bg_color = "#E0E0E0"
            text_color = "black"
        
        self.status_label.setStyleSheet(f"""
            font-weight: bold; 
            padding: 4px 12px; 
            border-radius: 4px;
            background-color: {bg_color};
            color: {text_color};
        """)
    
    def set_duration(self, duration: float):
        self.duration_label.setText(f"Duration: {duration:.2f}s")
    
    def clear(self):
        self.output_text.clear()
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("""
            font-weight: bold; 
            padding: 4px 12px; 
            border-radius: 4px;
            background-color: #E0E0E0;
            color: black;
        """)
        self.duration_label.setText("")
    
    def _copy_output(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())


# =============================================================================
# Main Window
# =============================================================================

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("cita-uiauto-engine")
        self.setMinimumSize(1100, 700)
        
        self._executor: Optional[CLIExecutor] = None
        self._subprocess_executor: Optional[SubprocessExecutor] = None
        self._build_ui()
    
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # HORIZONTAL Splitter: Left = Forms, Right = Output
        splitter = QSplitter(Qt.Horizontal)
        
        # LEFT: Tabs for commands
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        
        self.run_form = RunForm()
        self.run_form.command_ready.connect(self._execute_command)
        self.tabs.addTab(self.run_form, "Run")
        
        self.inspect_form = InspectForm()
        self.inspect_form.command_ready.connect(self._execute_command)
        self.tabs.addTab(self.inspect_form, "Inspect")
        
        self.record_form = RecordForm()
        self.record_form.command_ready.connect(self._execute_record)
        self.tabs.addTab(self.record_form, "Record")
        
        left_layout.addWidget(self.tabs)
        splitter.addWidget(left_widget)
        
        # RIGHT: Output viewer
        self.output_viewer = OutputViewer()
        splitter.addWidget(self.output_viewer)
        
        # Set initial sizes (left: 450px, right: remaining)
        splitter.setSizes([450, 650])
        splitter.setStretchFactor(0, 0)  # Left doesn't stretch
        splitter.setStretchFactor(1, 1)  # Right stretches
        
        main_layout.addWidget(splitter)
    
    def _execute_command(self, argv: list):
        """Execute run or inspect command."""
        self.output_viewer.clear()
        self.output_viewer.set_status("Running...", "orange")
        
        self._executor = CLIExecutor(argv)
        self._executor.output_received.connect(self.output_viewer.append_output)
        self._executor.finished_with_code.connect(self._on_command_finished)
        self._executor.start()
    
    def _execute_record(self, argv: list):
        """Execute record command (via subprocess)."""
        self.output_viewer.clear()
        self.output_viewer.set_status("Recording...", "orange")
        self.output_viewer.append_output("[Recording] Started. Press Ctrl+Alt+Q to stop.\n")
        
        self._subprocess_executor = SubprocessExecutor(argv)
        self._subprocess_executor.output_received.connect(self.output_viewer.append_output)
        self._subprocess_executor.finished_with_code.connect(self._on_record_finished)
        self._subprocess_executor.start()
    
    def _on_command_finished(self, return_code: int):
        """Handle completion of run/inspect commands."""
        if return_code == 0:
            self.output_viewer.set_status("PASSED", "green")
        elif return_code == 2:
            self.output_viewer.set_status("FAILED", "red")
        else:
            self.output_viewer.set_status("ERROR", "orange")
    
    def _on_record_finished(self, return_code: int):
        """Handle completion of record command."""
        # Reset button states
        self.record_form.start_btn.setEnabled(True)
        self.record_form.stop_btn.setEnabled(False)
        
        if return_code == 0:
            self.output_viewer.set_status("Recording Complete", "green")
            self.output_viewer.append_output("\n[Recording] Stopped successfully.")
        else:
            self.output_viewer.set_status("Recording Error", "orange")
            self.output_viewer.append_output(f"\n[Recording] Ended with code: {return_code}")
    
    def closeEvent(self, event):
        """Clean up on window close."""
        # Stop any running executor
        if self._executor and self._executor.isRunning():
            self._executor.terminate()
            self._executor.wait(1000)
        
        if self._subprocess_executor and self._subprocess_executor.isRunning():
            self._subprocess_executor.stop()
            self._subprocess_executor.wait(1000)
        
        event.accept()


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application metadata
    app.setApplicationName("cita-uiauto-engine")
    app.setApplicationVersion("1.2.0")
    app.setOrganizationName("cita")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()