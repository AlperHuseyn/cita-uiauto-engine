# uiauto_ui/forms/__init__.py
"""
Command input forms for cita-uiauto-engine GUI.
"""

from .base_form import BaseCommandForm
from .run_form import RunForm
from .inspect_form import InspectForm
from .record_form import RecordForm

__all__ = [
    "BaseCommandForm",
    "RunForm",
    "InspectForm",
    "RecordForm",
]