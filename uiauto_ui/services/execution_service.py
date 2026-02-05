# uiauto_ui/services/execution_service.py
"""
Execution orchestration service.
Manages the lifecycle of CLI command executions.
"""

from datetime import datetime
from typing import Optional, List, Callable

from PySide6.QtCore import QObject, Signal

from ..models.command_result import CommandResult
from ..models.execution_state import ExecutionState, ExecutionPhase
from ..cli_executor import BaseExecutor, create_executor
from ..status_mapping import get_status_for_return_code, get_status_for_phase, StatusInfo
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ExecutionService(QObject):
    """
    Service that orchestrates CLI command execution.
    
    Responsibilities:
    - Create and manage executors
    - Track execution state
    - Emit UI-friendly signals
    - Handle cancellation and cleanup
    
    Signals:
        execution_started: Emitted when execution begins
        output_received: Emitted for each line of output
        status_changed: Emitted when status changes
        execution_finished: Emitted when execution completes
    """
    
    # Signals for UI updates
    execution_started = Signal(str, list)  # command, argv
    output_received = Signal(str)          # line of output
    error_received = Signal(str)           # line of error
    status_changed = Signal(StatusInfo)    # new status
    execution_finished = Signal(CommandResult)  # final result
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._executor: Optional[BaseExecutor] = None
        self._state = ExecutionState()
    
    @property
    def is_running(self) -> bool:
        """True if an execution is in progress."""
        return self._state.is_running
    
    @property
    def current_command(self) -> Optional[str]:
        """The currently executing command, or None."""
        return self._state.command if self.is_running else None
    
    @property
    def can_cancel(self) -> bool:
        """True if the current execution can be cancelled."""
        return self._state.can_cancel and self._executor is not None
    
    def execute(self, command: str, argv: List[str]) -> bool:
        """
        Start executing a CLI command.
        
        Args:
            command: CLI command name (run, inspect, record, etc.)
            argv: Full argument list including command name
            
        Returns:
            True if execution started, False if already running
        """
        if self.is_running:
            logger.warning("Cannot start execution: already running")
            return False
        
        logger.info(f"Starting execution: {command}")
        
        # Update state
        self._state.start(command, argv)
        
        # Create executor
        self._executor = create_executor(command, argv, self)
        
        # Connect executor signals to our signals
        self._executor.signals.output_received.connect(self._on_output)
        self._executor.signals.error_received.connect(self._on_error)
        self._executor.signals.phase_changed.connect(self._on_phase_changed)
        self._executor.signals.finished.connect(self._on_finished)
        
        # Emit status
        if command == "record":
            self._state.phase = ExecutionPhase.RECORDING
            status = get_status_for_phase(ExecutionPhase.RECORDING)
        else:
            status = get_status_for_phase(ExecutionPhase.RUNNING)
        
        self.status_changed.emit(status)
        self.execution_started.emit(command, argv)
        
        # Start executor thread
        self._executor.start()
        return True
    
    def cancel(self) -> bool:
        """
        Cancel the current execution.
        
        Returns:
            True if cancellation was requested, False if not running
        """
        if not self.can_cancel:
            logger.warning("Cannot cancel: no execution in progress")
            return False
        
        logger.info("Cancelling execution...")
        self._executor.request_stop()
        self._state.phase = ExecutionPhase.STOPPING
        self.status_changed.emit(get_status_for_phase(ExecutionPhase.STOPPING))
        return True
    
    def cleanup(self) -> None:
        """
        Clean up any running executors.
        Call this before closing the application.
        """
        if self._executor is not None and self._executor.isRunning():
            logger.info("Cleaning up running executor...")
            self._executor.request_stop()
            self._executor.wait(3000)  # Wait up to 3 seconds
            if self._executor.isRunning():
                logger.warning("Executor did not stop gracefully, terminating...")
                self._executor.terminate()
                self._executor.wait(1000)
    
    def _on_output(self, line: str) -> None:
        """Handle output from executor."""
        self._state.append_output(line)
        self.output_received.emit(line)
    
    def _on_error(self, line: str) -> None:
        """Handle error output from executor."""
        self._state.append_error(line)
        self.error_received.emit(line)
    
    def _on_phase_changed(self, phase: ExecutionPhase) -> None:
        """Handle phase change from executor."""
        self._state.phase = phase
        status = get_status_for_phase(phase)
        if status:
            self.status_changed.emit(status)
    
    def _on_finished(self, result: CommandResult) -> None:
        """Handle execution completion."""
        logger.info(f"Execution finished: {result.command} → code={result.return_code}")
        
        # Update state
        self._state.complete(result.return_code)
        
        # Get final status
        status = get_status_for_return_code(result.command, result.return_code)
        self.status_changed.emit(status)
        
        # Emit result
        self.execution_finished.emit(result)
        
        # Cleanup executor reference
        self._executor = None