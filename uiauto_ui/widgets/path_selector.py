# uiauto_ui/widgets/path_selector.py
"""
Path selector widget with browse button.
Supports file, save, and directory modes.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton,
    QFileDialog, QCompleter
)
from PySide6.QtCore import Signal, QStringListModel


class PathSelector(QWidget):
    """
    File/directory path selector with browse button.
    
    Modes:
    - file: Select existing file
    - save: Select path for saving (file may not exist)
    - dir: Select directory
    
    Signals:
        path_changed: Emitted when path changes (str)
    """
    
    path_changed = Signal(str)
    
    def __init__(
        self,
        mode: str = "file",
        file_filter: str = "All Files (*)",
        placeholder: str = "",
        parent: Optional[QWidget] = None
    ):
        """
        Initialize path selector.
        
        Args:
            mode: Selection mode (file, save, dir)
            file_filter: Filter string for file dialogs
            placeholder: Placeholder text for input
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._mode = mode
        self._file_filter = file_filter
        
        self._build_ui(placeholder)
    
    def _build_ui(self, placeholder: str) -> None:
        """Build the widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Line edit for path
        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText(
            placeholder or f"Select {self._mode}..."
        )
        self._line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._line_edit, stretch=1)
        
        # Browse button
        self._browse_btn = QPushButton("...")
        self._browse_btn.setFixedWidth(30)
        self._browse_btn.setToolTip("Browse...")
        self._browse_btn.clicked.connect(self._browse)
        layout.addWidget(self._browse_btn)
    
    def _browse(self) -> None:
        """Open file/directory dialog."""
        start_dir = ""
        current = self._line_edit.text().strip()
        if current:
            path = Path(current)
            if path.exists():
                start_dir = str(path.parent if path.is_file() else path)
            elif path.parent.exists():
                start_dir = str(path.parent)
        
        if self._mode == "file":
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File",
                start_dir,
                self._file_filter
            )
        elif self._mode == "save":
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                start_dir,
                self._file_filter
            )
        elif self._mode == "dir":
            path = QFileDialog.getExistingDirectory(
                self,
                "Select Directory",
                start_dir
            )
        else:
            path = ""
        
        if path:
            self._line_edit.setText(path)
    
    def _on_text_changed(self, text: str) -> None:
        """Handle text changes."""
        self.path_changed.emit(text)
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def value(self) -> str:
        """Get the current path value."""
        return self._line_edit.text().strip()
    
    def set_value(self, value: str) -> None:
        """Set the path value."""
        self._line_edit.setText(value)
    
    def clear(self) -> None:
        """Clear the path."""
        self._line_edit.clear()
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._line_edit.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
    
    def set_placeholder(self, text: str) -> None:
        """Set placeholder text."""
        self._line_edit.setPlaceholderText(text)
    
    def set_recent_paths(self, paths: list) -> None:
        """Set recent paths for autocomplete."""
        completer = QCompleter(paths)
        self._line_edit.setCompleter(completer)
    
    @property
    def line_edit(self) -> QLineEdit:
        """Access to the underlying QLineEdit for signal connections."""
        return self._line_edit