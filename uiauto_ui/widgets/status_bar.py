# uiauto_ui/widgets/status_bar.py
"""
Status bar widget for displaying execution status.
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Signal

from ..status_mapping import StatusInfo, STATUS_READY


class StatusBar(QWidget):
    """
    Reusable status bar widget.
    
    Displays:
    - Status icon and label with colored background
    - Optional message text
    - Optional duration
    
    Signals:
        clicked: Emitted when status is clicked
    """
    
    clicked = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()
        self.set_status(STATUS_READY)
    
    def _build_ui(self) -> None:
        """Build the widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Status badge
        self._badge = QLabel()
        self._badge.setStyleSheet(self._get_badge_style(STATUS_READY))
        layout.addWidget(self._badge)
        
        # Message
        self._message = QLabel()
        self._message.setStyleSheet("color: #666;")
        layout.addWidget(self._message)
        
        layout.addStretch()
        
        # Duration
        self._duration = QLabel()
        self._duration.setStyleSheet("color: #666;")
        layout.addWidget(self._duration)
    
    def _get_badge_style(self, status: StatusInfo) -> str:
        """Get CSS style for status badge."""
        return f"""
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 4px;
            background-color: {status.bg_color};
            color: {status.text_color};
        """
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        self.clicked.emit()
        super().mousePressEvent(event)
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def set_status(self, status: StatusInfo) -> None:
        """
        Set the status display.
        
        Args:
            status: StatusInfo with display properties
        """
        self._badge.setText(f"{status.icon} {status.label}")
        self._badge.setStyleSheet(self._get_badge_style(status))
        self._badge.setToolTip(status.message)
    
    def set_message(self, message: str) -> None:
        """Set the message text."""
        self._message.setText(message)
    
    def set_duration(self, seconds: float) -> None:
        """Set the duration display."""
        if seconds <= 0:
            self._duration.setText("")
        elif seconds < 60:
            self._duration.setText(f"{seconds:.2f}s")
        else:
            minutes = int(seconds // 60)
            remaining = seconds % 60
            self._duration.setText(f"{minutes}m {remaining:.1f}s")
    
    def clear(self) -> None:
        """Reset to ready state."""
        self.set_status(STATUS_READY)
        self._message.setText("")
        self._duration.setText("")