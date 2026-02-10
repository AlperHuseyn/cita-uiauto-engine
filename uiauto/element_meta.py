# uiauto/element_meta.py

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ElementMeta:
    """
    Metadata describing how an element was resolved.

    This is immutable and used for debugging, error reporting,
    artifact generation, and future self-healing.
    """
    name: str
    window_name: str
    used_locator: Dict[str, Any] = field(default_factory=dict)
    found_via_name: bool = False
    resolution_strategy: Optional[str] = None
    attempt_index: int = 0
