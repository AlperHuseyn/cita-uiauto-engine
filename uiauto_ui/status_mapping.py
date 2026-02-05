# uiauto_ui/status_mapping.py
"""
Centralized status mapping for CLI return codes.
Single source of truth for status → UI representation.

NO Qt imports allowed - this is pure data/logic.
"""

from dataclasses import dataclass, replace
from enum import Enum
from typing import Dict, Optional

from .models.execution_state import ExecutionPhase


class StatusLevel(Enum):
    """Severity level for status display."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    RUNNING = "running"


@dataclass(frozen=True)
class StatusInfo:
    """
    Immutable status information for UI display.
    
    Attributes:
        level: Severity level
        label: Short label for status bar
        message: Detailed message for logs
        bg_color: Background color (hex)
        text_color: Text color (hex)
        icon: Emoji or icon identifier
    """
    level: StatusLevel
    label: str
    message: str
    bg_color: str
    text_color: str
    icon: str
    
    @property
    def is_success(self) -> bool:
        return self.level == StatusLevel.SUCCESS
    
    @property
    def is_error(self) -> bool:
        return self.level == StatusLevel.ERROR
    
    @property
    def is_running(self) -> bool:
        return self.level == StatusLevel.RUNNING


# =============================================================================
# Predefined Status Constants
# =============================================================================

STATUS_READY = StatusInfo(
    level=StatusLevel.INFO,
    label="Ready",
    message="Ready to execute",
    bg_color="#E0E0E0",
    text_color="#333333",
    icon="⏸️",
)

STATUS_RUNNING = StatusInfo(
    level=StatusLevel.RUNNING,
    label="Running...",
    message="Execution in progress",
    bg_color="#FF9800",
    text_color="#FFFFFF",
    icon="▶️",
)

STATUS_RECORDING = StatusInfo(
    level=StatusLevel.RUNNING,
    label="Recording...",
    message="Recording in progress (Ctrl+Alt+Q to stop)",
    bg_color="#FF5722",
    text_color="#FFFFFF",
    icon="🔴",
)

STATUS_STOPPING = StatusInfo(
    level=StatusLevel.WARNING,
    label="Stopping...",
    message="Graceful stop in progress",
    bg_color="#FFC107",
    text_color="#333333",
    icon="⏹️",
)

STATUS_VALIDATING = StatusInfo(
    level=StatusLevel.INFO,
    label="Validating...",
    message="Validating inputs",
    bg_color="#2196F3",
    text_color="#FFFFFF",
    icon="🔍",
)


# =============================================================================
# Return Code Mappings by Command
# =============================================================================

RUN_RETURN_CODES: Dict[int, StatusInfo] = {
    0: StatusInfo(
        level=StatusLevel.SUCCESS,
        label="PASSED",
        message="All scenario steps passed",
        bg_color="#4CAF50",
        text_color="#FFFFFF",
        icon="✅",
    ),
    1: StatusInfo(
        level=StatusLevel.WARNING,
        label="CONFIG ERROR",
        message="Configuration or validation error",
        bg_color="#FF9800",
        text_color="#FFFFFF",
        icon="⚠️",
    ),
    2: StatusInfo(
        level=StatusLevel.ERROR,
        label="FAILED",
        message="One or more scenario steps failed",
        bg_color="#F44336",
        text_color="#FFFFFF",
        icon="❌",
    ),
}

INSPECT_RETURN_CODES: Dict[int, StatusInfo] = {
    0: StatusInfo(
        level=StatusLevel.SUCCESS,
        label="SUCCESS",
        message="Inspection completed successfully",
        bg_color="#4CAF50",
        text_color="#FFFFFF",
        icon="✅",
    ),
    1: StatusInfo(
        level=StatusLevel.ERROR,
        label="ERROR",
        message="Inspection failed",
        bg_color="#F44336",
        text_color="#FFFFFF",
        icon="❌",
    ),
}

RECORD_RETURN_CODES: Dict[int, StatusInfo] = {
    0: StatusInfo(
        level=StatusLevel.SUCCESS,
        label="COMPLETE",
        message="Recording completed successfully",
        bg_color="#4CAF50",
        text_color="#FFFFFF",
        icon="✅",
    ),
    1: StatusInfo(
        level=StatusLevel.ERROR,
        label="ERROR",
        message="Recording failed or was interrupted",
        bg_color="#F44336",
        text_color="#FFFFFF",
        icon="❌",
    ),
    -1: StatusInfo(
        level=StatusLevel.WARNING,
        label="INTERRUPTED",
        message="Recording was interrupted by user",
        bg_color="#FF9800",
        text_color="#FFFFFF",
        icon="⏹️",
    ),
}

VALIDATE_RETURN_CODES: Dict[int, StatusInfo] = {
    0: StatusInfo(
        level=StatusLevel.SUCCESS,
        label="VALID",
        message="All files are valid",
        bg_color="#4CAF50",
        text_color="#FFFFFF",
        icon="✅",
    ),
    1: StatusInfo(
        level=StatusLevel.ERROR,
        label="INVALID",
        message="Validation failed",
        bg_color="#F44336",
        text_color="#FFFFFF",
        icon="❌",
    ),
}

# Registry of all command mappings
_COMMAND_STATUS_MAPS: Dict[str, Dict[int, StatusInfo]] = {
    "run": RUN_RETURN_CODES,
    "inspect": INSPECT_RETURN_CODES,
    "record": RECORD_RETURN_CODES,
    "validate": VALIDATE_RETURN_CODES,
    "list-elements": VALIDATE_RETURN_CODES,
}

# Unknown/fallback status
STATUS_UNKNOWN = StatusInfo(
    level=StatusLevel.WARNING,
    label="UNKNOWN",
    message="Unknown return code",
    bg_color="#9E9E9E",
    text_color="#FFFFFF",
    icon="❓",
)

STATUS_EXCEPTION = StatusInfo(
    level=StatusLevel.ERROR,
    label="EXCEPTION",
    message="Unexpected exception occurred",
    bg_color="#B71C1C",
    text_color="#FFFFFF",
    icon="💥",
)

STATUS_CANCELLED = StatusInfo(
    level=StatusLevel.WARNING,
    label="CANCELLED",
    message="Execution was cancelled",
    bg_color="#607D8B",
    text_color="#FFFFFF",
    icon="🚫",
)


# =============================================================================
# Public API
# =============================================================================

def get_status_for_return_code(command: str, return_code: int) -> StatusInfo:
    """
    Get status info for a command's return code.
    
    Args:
        command: CLI command name (run, inspect, record, etc.)
        return_code: Process exit code
        
    Returns:
        StatusInfo with appropriate display properties
    """
    status_map = _COMMAND_STATUS_MAPS.get(command, {})
    status = status_map.get(return_code)
    
    if status is not None:
        return status
    
    # Return unknown status with custom message
    return replace(STATUS_UNKNOWN, message=f"Unknown return code: {return_code}")


def get_status_for_phase(phase: ExecutionPhase) -> Optional[StatusInfo]:
    """
    Get status info for an execution phase.
    
    Args:
        phase: Current execution phase
        
    Returns:
        StatusInfo with appropriate display properties, or None
    """
    phase_map = {
        ExecutionPhase.IDLE: STATUS_READY,
        ExecutionPhase.VALIDATING: STATUS_VALIDATING,
        ExecutionPhase.STARTING: STATUS_RUNNING,
        ExecutionPhase.RUNNING: STATUS_RUNNING,
        ExecutionPhase.RECORDING: STATUS_RECORDING,
        ExecutionPhase.STOPPING: STATUS_STOPPING,
        ExecutionPhase.COMPLETED: None,  # Use return code instead
        ExecutionPhase.FAILED: None,     # Use return code instead
        ExecutionPhase.CANCELLED: STATUS_CANCELLED,
        ExecutionPhase.ERROR: STATUS_EXCEPTION,
    }
    return phase_map.get(phase, STATUS_UNKNOWN)


def get_status_for_exception(exception: Exception) -> StatusInfo:
    """
    Get status info for an exception.
    
    Args:
        exception: The exception that occurred
        
    Returns:
        StatusInfo for exception display
    """
    return StatusInfo(
        level=StatusLevel.ERROR,
        label="EXCEPTION",
        message=f"{type(exception).__name__}: {exception}",
        bg_color="#B71C1C",
        text_color="#FFFFFF",
        icon="💥",
    )