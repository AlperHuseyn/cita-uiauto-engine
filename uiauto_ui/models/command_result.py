# uiauto_ui/models/command_result.py
"""
Command execution result model.
Immutable data container for CLI execution outcomes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass(frozen=True)
class CommandResult:
    """
    Immutable result of a CLI command execution.
    
    Attributes:
        command: The command name (run, inspect, record)
        argv: Full argument list passed to CLI
        return_code: Process exit code (0 = success)
        output: Captured stdout content
        errors: Captured stderr content
        started_at: Execution start timestamp
        finished_at: Execution end timestamp
        exception: Exception message if crashed
    """
    command: str
    argv: List[str]
    return_code: int
    output: str = ""
    errors: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exception: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """True if command completed successfully (return code 0)."""
        return self.return_code == 0
    
    @property
    def duration_seconds(self) -> float:
        """Execution duration in seconds."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0
    
    @property
    def duration_formatted(self) -> str:
        """Human-readable duration string."""
        seconds = self.duration_seconds
        if seconds < 60:
            return f"{seconds:.2f}s"
        minutes = int(seconds // 60)
        remaining = seconds % 60
        return f"{minutes}m {remaining:.1f}s"
    
    @property
    def has_errors(self) -> bool:
        """True if there are error messages or non-zero return code."""
        return bool(self.errors) or self.return_code != 0 or self.exception is not None
    
    def to_log_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "command": self.command,
            "argv": self.argv,
            "return_code": self.return_code,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "has_errors": self.has_errors,
            "exception": self.exception,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }