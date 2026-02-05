# uiauto_ui/app.py
"""
Main application entry point for cita-uiauto-engine GUI.

This module contains ONLY:
- QApplication initialization
- MainWindow class with UI wiring
- Signal routing between components
- NO business logic

All business logic is delegated to services and forms.
"""

import sys
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt

from .forms import RunForm, InspectForm, RecordForm
from .widgets.output_viewer import OutputViewer
from .widgets.status_bar import StatusBar
from .services.execution_service import ExecutionService
from .services.settings_service import SettingsService
from .models.command_result import CommandResult
from .status_mapping import StatusInfo, STATUS_READY, STATUS_RECORDING
from .utils.logging import setup_logging, get_logger

# Initialize logging before anything else
setup_logging()
logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Responsibilities:
    - Layout and widget placement
    - Signal routing between forms and services
    - Window state persistence
    - Graceful shutdown
    
    Does NOT contain business logic - delegates to services.
    """
    
    def __init__(self):
        super().__init__()
        
        logger.info("Initializing MainWindow")
        
        # Initialize services
        self._execution_service = ExecutionService(self)
        self._settings_service = SettingsService()
        
        # Build UI
        self._build_ui()
        self._connect_signals()
        
        # Restore window state
        self._restore_state()
        
        logger.info("MainWindow initialized")
    
    def _build_ui(self) -> None:
        """Build the main window UI."""
        self.setWindowTitle("cita-uiauto-engine")
        self.setMinimumSize(1100, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Horizontal splitter: Left = Forms, Right = Output
        self._splitter = QSplitter(Qt.Horizontal)
        
        # LEFT: Tab widget with command forms
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self._tabs = QTabWidget()
        
        # Run form
        self._run_form = RunForm()
        self._tabs.addTab(self._run_form, "Run")
        
        # Inspect form
        self._inspect_form = InspectForm()
        self._tabs.addTab(self._inspect_form, "Inspect")
        
        # Record form
        self._record_form = RecordForm()
        self._tabs.addTab(self._record_form, "Record")
        
        left_layout.addWidget(self._tabs)
        self._splitter.addWidget(left_widget)
        
        # RIGHT: Output viewer
        self._output_viewer = OutputViewer()
        self._splitter.addWidget(self._output_viewer)
        
        # Splitter sizing
        self._splitter.setSizes([450, 650])
        self._splitter.setStretchFactor(0, 0)  # Left doesn't stretch
        self._splitter.setStretchFactor(1, 1)  # Right stretches
        
        main_layout.addWidget(self._splitter)
        
        # Status bar at bottom
        self._status_bar = StatusBar()
        main_layout.addWidget(self._status_bar)
    
    def _connect_signals(self) -> None:
        """Connect signals between components."""
        
        # Form command signals -> execution service
        self._run_form.command_requested.connect(self._on_command_requested)
        self._inspect_form.command_requested.connect(self._on_command_requested)
        self._record_form.command_requested.connect(self._on_record_requested)
        self._record_form.stop_requested.connect(self._on_stop_requested)
        
        # Execution service signals -> UI
        self._execution_service.output_received.connect(
            self._output_viewer.append_line
        )
        self._execution_service.error_received.connect(
            lambda line: self._output_viewer.append_output(line, "error")
        )
        self._execution_service.status_changed.connect(self._on_status_changed)
        self._execution_service.execution_finished.connect(self._on_execution_finished)
        
        # Tab changes
        self._tabs.currentChanged.connect(self._on_tab_changed)
        
        # Status bar click
        self._status_bar.clicked.connect(self._on_status_clicked)
    
    def _restore_state(self) -> None:
        """Restore window state from settings."""
        # Window geometry
        geometry = self._settings_service.load_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        
        # Splitter state
        splitter_state = self._settings_service.load_splitter_state()
        if splitter_state:
            self._splitter.restoreState(splitter_state)
        
        # Last active tab
        last_tab = self._settings_service.load_last_tab()
        if 0 <= last_tab < self._tabs.count():
            self._tabs.setCurrentIndex(last_tab)
        
        # Load last used paths into forms
        self._run_form.load_last_paths(self._settings_service)
    
    def _save_state(self) -> None:
        """Save window state to settings."""
        self._settings_service.save_window_geometry(self.saveGeometry())
        self._settings_service.save_splitter_state(self._splitter.saveState())
        self._settings_service.save_last_tab(self._tabs.currentIndex())
        
        # Save last used paths
        self._run_form.save_last_paths(self._settings_service)
    
    # -------------------------------------------------------------------------
    # Signal Handlers
    # -------------------------------------------------------------------------
    
    def _on_command_requested(self, argv: list) -> None:
        """Handle run/inspect command request from forms."""
        if not argv:
            return
        
        command = argv[0]
        logger.info(f"Command requested: {command}")
        
        # Clear output and set running state
        self._output_viewer.clear()
        self._output_viewer.start_timing()
        
        # Disable form while running
        current_form = self._tabs.currentWidget()
        if hasattr(current_form, 'set_running'):
            current_form.set_running(True)
        
        # Execute command
        self._execution_service.execute(command, argv)
    
    def _on_record_requested(self, argv: list) -> None:
        """Handle record command request."""
        if not argv:
            return
        
        logger.info("Record command requested")
        
        # Clear output and show recording status
        self._output_viewer.clear()
        self._output_viewer.start_timing()
        self._output_viewer.append_output(
            "Recording started. Press Ctrl+Alt+Q to stop.",
            "info"
        )
        
        # Set recording state
        self._record_form.set_recording(True)
        
        # Execute record command
        self._execution_service.execute("record", argv)
    
    def _on_stop_requested(self) -> None:
        """Handle stop request from record form."""
        logger.info("Stop requested")
        self._execution_service.cancel()
    
    def _on_status_changed(self, status: StatusInfo) -> None:
        """Handle status change from execution service."""
        self._status_bar.set_status(status)
    
    def _on_execution_finished(self, result: CommandResult) -> None:
        """Handle execution completion."""
        logger.info(
            f"Execution finished: {result.command} -> code={result.return_code}"
        )
        
        # Update duration display
        self._output_viewer.set_duration(result.duration_seconds)
        
        # Reset form state
        current_form = self._tabs.currentWidget()
        if hasattr(current_form, 'set_running'):
            current_form.set_running(False)
        
        # Special handling for record
        if result.command == "record":
            self._record_form.set_recording(False)
            if result.success:
                self._output_viewer.append_output(
                    "Recording completed successfully!",
                    "success"
                )
            else:
                self._output_viewer.append_output(
                    f"Recording ended with code: {result.return_code}",
                    "warning"
                )
    
    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change."""
        # Could be used to update status or other UI elements
        pass
    
    def _on_status_clicked(self) -> None:
        """Handle status bar click."""
        # Could show detailed status dialog
        pass
    
    # -------------------------------------------------------------------------
    # Window Events
    # -------------------------------------------------------------------------
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        logger.info("Window closing...")
        
        # Check if execution is running
        if self._execution_service.is_running:
            response = QMessageBox.question(
                self,
                "Execution in Progress",
                "A command is still running. Cancel and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if response != QMessageBox.Yes:
                event.ignore()
                return
            
            # Cancel execution
            self._execution_service.cancel()
        
        # Cleanup
        self._execution_service.cleanup()
        
        # Save state
        self._save_state()
        
        logger.info("Window closed")
        event.accept()


def main() -> int:
    """
    Application entry point.
    
    Returns:
        Exit code (0 = success)
    """
    logger.info("Starting cita-uiauto-engine UI")
    
    # Create application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Application metadata
    app.setApplicationName("cita-uiauto-engine")
    app.setApplicationVersion("1.2.0")
    app.setOrganizationName("cita")
    app.setOrganizationDomain("cita.io")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    exit_code = app.exec()
    
    logger.info(f"Application exiting with code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())