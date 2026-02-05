# uiauto_ui/models/execution_state.py
"""
Execution state model for tracking command lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List


class ExecutionPhase(Enum):
    """Phases of command execution lifecycle."""
    IDLE = auto()           # No execution in progress
    VALIDATING = auto()     # Validating inputs
    STARTING = auto()       # Starting execution
    RUNNING = auto()        # Command is running
    RECORDING = auto()      # Recording in progress (special for record command)
    STOPPING = auto()       # Graceful stop requested
    COMPLETED = auto()      # Execution finished successfully
    FAILED = auto()         # Execution failed
    CANCELLED = auto()      # User cancelled
    ERROR = auto()          # Unexpected error occurred


@dataclass
class ExecutionState:
    """
    Mutable state container for tracking execution progress.
    
    Used by ExecutionService to track current execution status
    and emit appropriate signals.
    """
    phase: ExecutionPhase = ExecutionPhase.IDLE
    command: Optional[str] = None
    argv: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    output_lines: List[str] = field(default_factory=list)
    error_lines: List[str] = field(default_factory=list)
    return_code: Optional[int] = None
    exception: Optional[str] = None
    
    @property
    def is_running(self) -> bool:
        """True if execution is in progress."""
        return self.phase in (
            ExecutionPhase.VALIDATING,
            ExecutionPhase.STARTING,
            ExecutionPhase.RUNNING,
            ExecutionPhase.RECORDING,
            ExecutionPhase.STOPPING,
        )
    
    @property
    def is_terminal(self) -> bool:
        """True if execution has reached a terminal state."""
        return self.phase in (
            ExecutionPhase.IDLE,
            ExecutionPhase.COMPLETED,
            ExecutionPhase.FAILED,
            ExecutionPhase.CANCELLED,
            ExecutionPhase.ERROR,
        )
    
    @property
    def can_cancel(self) -> bool:
        """True if execution can be cancelled."""
        return self.is_running
    
    def reset(self) -> None:
        """Reset to idle state."""
        self.phase = ExecutionPhase.IDLE
        self.command = None
        self.argv = []
        self.started_at = None
        self.output_lines = []
        self.error_lines = []
        self.return_code = None
        self.exception = None
    
    def start(self, command: str, argv: List[str]) -> None:
        """Transition to starting state."""
        self.reset()
        self.phase = ExecutionPhase.STARTING
        self.command = command
        self.argv = argv
        self.started_at = datetime.now()
    
    def append_output(self, line: str) -> None:
        """Append output line."""
        self.output_lines.append(line)
    
    def append_error(self, line: str) -> None:
        """Append error line."""
        self.error_lines.append(line)
    
    def complete(self, return_code: int) -> None:
        """Transition to completed/failed state."""
        self.return_code = return_code
        if return_code == 0:
            self.phase = ExecutionPhase.COMPLETED
        else:
            self.phase = ExecutionPhase.FAILED
    
    def error(self, exception: str) -> None:
        """Transition to error state."""
        self.phase = ExecutionPhase.ERROR
        self.exception = exception
    
    def cancel(self) -> None:
        """Transition to cancelled state."""
        self.phase = ExecutionPhase.CANCELLED