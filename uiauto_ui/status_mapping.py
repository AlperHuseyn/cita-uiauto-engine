# uiauto_ui/status_mapping.py
"""
Maps CLI return codes to UI status messages and colors.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class StatusLevel(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


@dataclass
class StatusInfo:
    """Status information for UI display."""
    level: StatusLevel
    message: str
    color: str
    icon: str


# =============================================================================
# Return Code Mappings
# =============================================================================

RUN_STATUS_MAP = {
    0: StatusInfo(StatusLevel.SUCCESS, "PASSED", "#4CAF50", "✅"),
    1: StatusInfo(StatusLevel.ERROR, "CONFIG ERROR", "#FF9800", "⚠️"),
    2: StatusInfo(StatusLevel.ERROR, "FAILED", "#F44336", "❌"),
}

INSPECT_STATUS_MAP = {
    0: StatusInfo(StatusLevel.SUCCESS, "SUCCESS", "#4CAF50", "✅"),
    1: StatusInfo(StatusLevel.ERROR, "ERROR", "#F44336", "❌"),
}

RECORD_STATUS_MAP = {
    0: StatusInfo(StatusLevel.SUCCESS, "RECORDING COMPLETE", "#4CAF50", "✅"),
    1: StatusInfo(StatusLevel.ERROR, "RECORDING ERROR", "#F44336", "❌"),
}

VALIDATE_STATUS_MAP = {
    0: StatusInfo(StatusLevel.SUCCESS, "VALID", "#4CAF50", "✅"),
    1: StatusInfo(StatusLevel.ERROR, "INVALID", "#F44336", "❌"),
}


def get_status(command: str, return_code: int) -> StatusInfo:
    """Get status info for command and return code."""
    maps = {
        "run": RUN_STATUS_MAP,
        "inspect": INSPECT_STATUS_MAP,
        "record": RECORD_STATUS_MAP,
        "validate": VALIDATE_STATUS_MAP,
        "list-elements": VALIDATE_STATUS_MAP,
    }
    
    status_map = maps.get(command, {})
    
    return status_map.get(return_code, StatusInfo(
        StatusLevel.WARNING,
        f"UNKNOWN (code={return_code})",
        "#9E9E9E",
        "❓"
    ))