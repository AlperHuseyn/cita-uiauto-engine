# uiauto_ui/widgets/key_value_table.py
"""
Key-value table widget for variable input.
"""

from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView
)
from PySide6.QtCore import Signal


class KeyValueTable(QWidget):
    """
    Table widget for key=value pair input.
    
    Used for:
    - --var KEY=VALUE arguments
    - Environment variables
    - Configuration overrides
    
    Signals:
        values_changed: Emitted when values change
    """
    
    values_changed = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Table
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Key", "Value"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setMinimumHeight(80)
        self._table.setMaximumHeight(150)
        self._table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("+")
        add_btn.setFixedWidth(30)
        add_btn.setToolTip("Add row")
        add_btn.clicked.connect(self.add_row)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("-")
        remove_btn.setFixedWidth(30)
        remove_btn.setToolTip("Remove selected row")
        remove_btn.clicked.connect(self.remove_selected_row)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _on_cell_changed(self, row: int, column: int) -> None:
        """Handle cell value changes."""
        self.values_changed.emit()
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def add_row(self, key: str = "", value: str = "") -> None:
        """
        Add a new row to the table.
        
        Args:
            key: Initial key value
            value: Initial value
        """
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(key))
        self._table.setItem(row, 1, QTableWidgetItem(value))
        self.values_changed.emit()
    
    def remove_selected_row(self) -> None:
        """Remove the currently selected row."""
        current = self._table.currentRow()
        if current >= 0:
            self._table.removeRow(current)
            self.values_changed.emit()
    
    def clear(self) -> None:
        """Remove all rows."""
        self._table.setRowCount(0)
        self.values_changed.emit()
    
    def values(self) -> List[str]:
        """
        Get values as KEY=VALUE strings.
        
        Returns:
            List of "KEY=VALUE" strings
        """
        result = []
        for row in range(self._table.rowCount()):
            key_item = self._table.item(row, 0)
            val_item = self._table.item(row, 1)
            
            if key_item and val_item:
                key = key_item.text().strip()
                val = val_item.text().strip()
                if key:
                    result.append(f"{key}={val}")
        
        return result
    
    def values_dict(self) -> dict:
        """
        Get values as dictionary.
        
        Returns:
            Dictionary of key-value pairs
        """
        result = {}
        for row in range(self._table.rowCount()):
            key_item = self._table.item(row, 0)
            val_item = self._table.item(row, 1)
            
            if key_item and val_item:
                key = key_item.text().strip()
                val = val_item.text().strip()
                if key:
                    result[key] = val
        
        return result
    
    def set_values(self, values: List[str]) -> None:
        """
        Set values from KEY=VALUE strings.
        
        Args:
            values: List of "KEY=VALUE" strings
        """
        self.clear()
        for item in values:
            if "=" in item:
                key, value = item.split("=", 1)
                self.add_row(key.strip(), value.strip())
    
    def set_values_dict(self, values: dict) -> None:
        """
        Set values from dictionary.
        
        Args:
            values: Dictionary of key-value pairs
        """
        self.clear()
        for key, value in values.items():
            self.add_row(str(key), str(value))
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._table.setEnabled(enabled)