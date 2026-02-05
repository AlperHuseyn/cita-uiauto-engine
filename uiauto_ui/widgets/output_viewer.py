# uiauto_ui/widgets/output_viewer.py
"""
Output viewer widget for displaying CLI output.
Supports timestamped output, auto-scroll, and status display.
"""

from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QApplication, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ..status_mapping import StatusInfo, STATUS_READY


class OutputViewer(QWidget):
    """
    Widget for displaying CLI output with status.
    
    Features:
    - Timestamped output lines
    - Auto-scroll with user override
    - Status indicator with color
    - Duration display
    - Copy/Clear buttons
    
    Signals:
        cleared: Emitted when output is cleared
    """
    
    cleared = Signal()
    
    # Color scheme for output
    COLORS = {
        "default": "#D4D4D4",
        "error": "#F44336",
        "warning": "#FF9800",
        "success": "#4CAF50",
        "info": "#2196F3",
        "timestamp": "#808080",
    }
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._auto_scroll = True
        self._user_scrolled = False
        self._start_time: Optional[datetime] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header with status
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Output")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(self._get_status_style(STATUS_READY))
        header_layout.addWidget(self._status_label)
        
        # Duration display
        self._duration_label = QLabel("")
        self._duration_label.setStyleSheet("color: #666; margin-left: 8px;")
        header_layout.addWidget(self._duration_label)
        
        layout.addLayout(header_layout)
        
        # Output text area
        self._output_text = QTextEdit()
        self._output_text.setReadOnly(True)
        self._output_text.setFont(QFont("Consolas", 10))
        self._output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        # Track scroll position to detect user scrolling
        self._output_text.verticalScrollBar().valueChanged.connect(
            self._on_scroll_changed
        )
        
        layout.addWidget(self._output_text)
        
        # Footer with buttons
        footer_layout = QHBoxLayout()
        
        # Auto-scroll toggle
        self._auto_scroll_cb = QCheckBox("Auto-scroll")
        self._auto_scroll_cb.setChecked(True)
        self._auto_scroll_cb.stateChanged.connect(self._on_auto_scroll_changed)
        footer_layout.addWidget(self._auto_scroll_cb)
        
        footer_layout.addStretch()
        
        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.setToolTip("Copy output to clipboard")
        copy_btn.clicked.connect(self._copy_output)
        footer_layout.addWidget(copy_btn)
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setToolTip("Clear output")
        clear_btn.clicked.connect(self.clear)
        footer_layout.addWidget(clear_btn)
        
        layout.addLayout(footer_layout)
    
    def _get_status_style(self, status: StatusInfo) -> str:
        """Get CSS style for status label."""
        return f"""
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 4px;
            background-color: {status.bg_color};
            color: {status.text_color};
        """
    
    def _on_scroll_changed(self, value: int) -> None:
        """Handle scroll bar value changes."""
        scrollbar = self._output_text.verticalScrollBar()
        # If user scrolled away from bottom, disable auto-scroll
        if value < scrollbar.maximum() - 20:
            self._user_scrolled = True
            self._auto_scroll_cb.setChecked(False)
        elif value >= scrollbar.maximum() - 20:
            self._user_scrolled = False
    
    def _on_auto_scroll_changed(self, state: int) -> None:
        """Handle auto-scroll checkbox changes."""
        self._auto_scroll = (state == Qt.Checked)
        if self._auto_scroll:
            self._scroll_to_bottom()
    
    def _scroll_to_bottom(self) -> None:
        """Scroll output to bottom."""
        scrollbar = self._output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _copy_output(self) -> None:
        """Copy output to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._output_text.toPlainText())
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def append_output(self, text: str, color: str = "default") -> None:
        """
        Append text to output with optional color.
        
        Args:
            text: Text to append
            color: Color key (default, error, warning, success, info)
        """
        # Get color
        text_color = self.COLORS.get(color, self.COLORS["default"])
        
        # Format with timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamp_color = self.COLORS["timestamp"]
        
        # Build HTML
        html = f'<span style="color: {timestamp_color}">[{timestamp}]</span> '
        html += f'<span style="color: {text_color}">{text}</span>'
        
        # Append
        self._output_text.append(html)
        
        # Auto-scroll if enabled
        if self._auto_scroll and not self._user_scrolled:
            self._scroll_to_bottom()
    
    def append_line(self, text: str) -> None:
        """
        Append a plain line of output.
        
        Args:
            text: Text to append
        """
        # Detect color from content
        lower = text.lower()
        if "[error]" in lower or "error:" in lower or "failed" in lower:
            color = "error"
        elif "[warning]" in lower or "warning:" in lower:
            color = "warning"
        elif "[success]" in lower or "passed" in lower:
            color = "success"
        elif "[info]" in lower:
            color = "info"
        else:
            color = "default"
        
        self.append_output(text, color)
    
    def set_status(self, status: StatusInfo) -> None:
        """
        Set the status display.
        
        Args:
            status: StatusInfo with display properties
        """
        self._status_label.setText(f"{status.icon} {status.label}")
        self._status_label.setStyleSheet(self._get_status_style(status))
        self._status_label.setToolTip(status.message)
    
    def set_duration(self, seconds: float) -> None:
        """
        Set the duration display.
        
        Args:
            seconds: Duration in seconds
        """
        if seconds < 60:
            text = f"{seconds:.2f}s"
        else:
            minutes = int(seconds // 60)
            remaining = seconds % 60
            text = f"{minutes}m {remaining:.1f}s"
        
        self._duration_label.setText(f"Duration: {text}")
    
    def start_timing(self) -> None:
        """Start timing for duration display."""
        self._start_time = datetime.now()
        self._duration_label.setText("")
    
    def stop_timing(self) -> None:
        """Stop timing and display duration."""
        if self._start_time:
            duration = (datetime.now() - self._start_time).total_seconds()
            self.set_duration(duration)
            self._start_time = None
    
    def clear(self) -> None:
        """Clear all output and reset status."""
        self._output_text.clear()
        self._status_label.setText("Ready")
        self._status_label.setStyleSheet(self._get_status_style(STATUS_READY))
        self._duration_label.setText("")
        self._start_time = None
        self._user_scrolled = False
        self._auto_scroll_cb.setChecked(True)
        self.cleared.emit()
    
    def get_text(self) -> str:
        """Get plain text content."""
        return self._output_text.toPlainText()
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._output_text.setEnabled(enabled)