# uiauto_ui/forms/base_form.py
"""
Base class for command forms.
Forms collect user input but never execute commands directly.
"""

from typing import List, Tuple, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout,
    QHBoxLayout, QPushButton, QMessageBox
)
from PySide6.QtCore import Signal

from ..widgets.command_preview import CommandPreview
from ..services.validation_service import ValidationResult


class BaseCommandForm(QWidget):
    """
    Base class for command input forms.
    
    Responsibilities:
    - Collect user input
    - Build CLI argv
    - Validate inputs
    - Emit signals when ready to execute
    
    Subclasses must implement:
    - _build_form(): Build form-specific widgets
    - _collect_values(): Collect current form values
    - _get_command_name(): Return command name
    
    Signals:
        command_requested: Emitted when user wants to run (argv: List[str])
        validation_requested: Emitted when user wants to validate
        values_changed: Emitted when any form value changes
    """
    
    # Signals
    command_requested = Signal(list)      # argv list
    validation_requested = Signal()
    values_changed = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._is_running = False
        self._widgets: Dict[str, QWidget] = {}
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self) -> None:
        """Build the complete form UI."""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(5, 5, 5, 5)
        self._main_layout.setSpacing(8)
        
        # Let subclass build form content
        self._build_form()
        
        # Command preview (common to all forms)
        self._build_preview_section()
        
        # Action buttons (common to all forms)
        self._build_button_section()
        
        # Add stretch at the end
        self._main_layout.addStretch()
        
        # Initial preview update
        self._update_preview()
    
    def _build_form(self) -> None:
        """
        Build form-specific widgets.
        Subclasses add their widgets to self._main_layout.
        """
        raise NotImplementedError("Subclasses must implement _build_form()")
    
    def _collect_values(self) -> Dict[str, Any]:
        """
        Collect current form values.
        
        Returns:
            Dictionary of field_name -> value
        """
        raise NotImplementedError("Subclasses must implement _collect_values()")
    
    def _get_command_name(self) -> str:
        """
        Get the CLI command name.
        
        Returns:
            Command name (e.g., 'run', 'inspect', 'record')
        """
        raise NotImplementedError("Subclasses must implement _get_command_name()")
    
    def _build_preview_section(self) -> None:
        """Build command preview section."""
        preview_group = QGroupBox("Generated Command")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        
        self._command_preview = CommandPreview()
        preview_layout.addWidget(self._command_preview)
        
        self._main_layout.addWidget(preview_group)
    
    def _build_button_section(self) -> None:
        """Build action button section."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # Validate button (optional, can be hidden by subclass)
        self._validate_btn = QPushButton("Validate")
        self._validate_btn.setToolTip("Validate form inputs")
        self._validate_btn.clicked.connect(self._on_validate_clicked)
        btn_layout.addWidget(self._validate_btn)
        
        # Primary action button
        self._run_btn = self._create_run_button()
        self._run_btn.clicked.connect(self._on_run_clicked)
        btn_layout.addWidget(self._run_btn)
        
        self._main_layout.addLayout(btn_layout)
    
    def _create_run_button(self) -> QPushButton:
        """
        Create the primary action button.
        Subclasses can override for custom styling.
        """
        btn = QPushButton("Run")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #9E9E9E;
            }
        """)
        return btn
    
    def _connect_signals(self) -> None:
        """
        Connect widget signals for live preview.
        Subclasses should call this after adding widgets.
        """
        # This will be called after _build_form, so widgets exist
        pass
    
    def _update_preview(self) -> None:
        """Update command preview with current values."""
        try:
            argv = self.build_argv()
            self._command_preview.set_argv(argv)
        except Exception:
            self._command_preview.set_text("(incomplete)")
    
    def _on_validate_clicked(self) -> None:
        """Handle validate button click."""
        result = self.validate()
        
        if result.is_valid:
            QMessageBox.information(
                self, 
                "Validation Passed",
                "All inputs are valid!"
            )
        else:
            QMessageBox.warning(
                self,
                "Validation Failed",
                result.all_messages
            )
        
        self.validation_requested.emit()
    
    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        result = self.validate()
        
        if not result.is_valid:
            QMessageBox.warning(
                self,
                "Validation Error",
                result.error_message
            )
            return
        
        # Show warnings but allow continue
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
        
        argv = self.build_argv()
        self.command_requested.emit(argv)
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def build_argv(self) -> List[str]:
        """
        Build CLI argument list from form values.
        
        Returns:
            List of command line arguments
        """
        from ..commands import ArgBuilder, get_command
        
        values = self._collect_values()
        command_spec = get_command(self._get_command_name())
        
        builder = ArgBuilder(command_spec)
        for name, value in values.items():
            builder.set(name, value)
        
        return builder.build()
    
    def validate(self) -> ValidationResult:
        """
        Validate form inputs.
        
        Returns:
            ValidationResult with errors and warnings
        """
        from ..services.validation_service import ValidationService
        
        service = ValidationService()
        values = self._collect_values()
        command_name = self._get_command_name()
        
        return service.validate_command(command_name, values)
    
    def set_running(self, is_running: bool) -> None:
        """
        Set form running state.
        Disables inputs while running.
        
        Args:
            is_running: True if command is executing
        """
        self._is_running = is_running
        self._run_btn.setEnabled(not is_running)
        self._validate_btn.setEnabled(not is_running)
        
        # Disable all input widgets
        for widget in self._widgets.values():
            if hasattr(widget, 'setEnabled'):
                widget.setEnabled(not is_running)
    
    def get_values(self) -> Dict[str, Any]:
        """
        Get current form values.
        
        Returns:
            Dictionary of form values
        """
        return self._collect_values()
    
    def set_values(self, values: Dict[str, Any]) -> None:
        """
        Set form values.
        Subclasses should override to populate widgets.
        
        Args:
            values: Dictionary of field_name -> value
        """
        pass
    
    def reset(self) -> None:
        """Reset form to default values."""
        pass
    
    # -------------------------------------------------------------------------
    # Helper Methods for Subclasses
    # -------------------------------------------------------------------------
    
    def _create_group(self, title: str) -> Tuple[QGroupBox, QFormLayout]:
        """
        Create a form group box.
        
        Args:
            title: Group box title
            
        Returns:
            Tuple of (QGroupBox, QFormLayout)
        """
        group = QGroupBox(title)
        layout = QFormLayout(group)
        layout.setSpacing(8)
        return group, layout
    
    def _create_collapsible_group(
        self, 
        title: str, 
        collapsed: bool = True
    ) -> Tuple[QGroupBox, QFormLayout]:
        """
        Create a collapsible form group box.
        
        Args:
            title: Group box title
            collapsed: Initial collapsed state
            
        Returns:
            Tuple of (QGroupBox, QFormLayout)
        """
        group = QGroupBox(title)
        group.setCheckable(True)
        group.setChecked(not collapsed)
        layout = QFormLayout(group)
        layout.setSpacing(8)
        return group, layout
    
    def _register_widget(self, name: str, widget: QWidget) -> QWidget:
        """
        Register a widget for state management.
        
        Args:
            name: Widget identifier
            widget: The widget instance
            
        Returns:
            The widget (for chaining)
        """
        self._widgets[name] = widget
        return widget