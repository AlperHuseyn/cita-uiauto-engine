# uiauto_ui/widgets/command_preview.py
"""
Command preview widget for displaying generated CLI commands.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton,
    QHBoxLayout, QApplication
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont


class CommandPreview(QWidget):
    """
    Widget for previewing generated CLI commands.
    
    Features:
    - Syntax highlighted command display
    - Multi-line formatting
    - Copy button
    
    Signals:
        copy_requested: Emitted when copy is clicked
    """
    
    copy_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Command text area
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setMaximumHeight(120)
        self._text_edit.setFont(QFont("Consolas", 9))
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self._text_edit)
        
        # Copy button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        copy_btn = QPushButton("Copy Command")
        copy_btn.setFixedWidth(120)
        copy_btn.clicked.connect(self._copy)
        btn_layout.addWidget(copy_btn)
        
        layout.addLayout(btn_layout)
    
    def _copy(self) -> None:
        """Copy command to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.get_command_text())
        self.copy_requested.emit()
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def set_argv(self, argv: List[str]) -> None:
        """
        Set command from argv list.
        
        Args:
            argv: Command line arguments
        """
        if not argv:
            self._text_edit.setText("(incomplete)")
            return
        
        # Format as multi-line command
        formatted = self._format_command(argv)
        self._text_edit.setText(formatted)
    
    def _format_command(self, argv: List[str]) -> str:
        """Format argv as readable multi-line command."""
        if not argv:
            return "(incomplete)"
        
        lines = ["python -m uiauto.cli \\"]
        lines.append(f"    {argv[0]} \\")  # Command name
        
        i = 1
        while i < len(argv):
            arg = argv[i]
            
            if arg.startswith("--"):
                # Check if next item is a value
                if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                    value = argv[i + 1]
                    # Quote values with spaces
                    if " " in value:
                        value = f'"{value}"'
                    lines.append(f"    {arg} {value} \\")
                    i += 2
                else:
                    lines.append(f"    {arg} \\")
                    i += 1
            else:
                # Positional argument
                value = arg
                if " " in value:
                    value = f'"{value}"'
                lines.append(f"    {value} \\")
                i += 1
        
        # Remove trailing backslash from last line
        if lines:
            lines[-1] = lines[-1].rstrip(" \\")
        
        return "\n".join(lines)
    
    def set_text(self, text: str) -> None:
        """Set raw text content."""
        self._text_edit.setText(text)
    
    def get_command_text(self) -> str:
        """Get the command as single-line text."""
        text = self._text_edit.toPlainText()
        # Convert multi-line to single line
        return text.replace(" \\\n", " ").replace("\n", " ").strip()
    
    def clear(self) -> None:
        """Clear the preview."""
        self._text_edit.clear()