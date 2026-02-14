# uiauto/context.py
"""
@file context.py
@brief Action context management for rich error messages and debugging.
"""

from __future__ import annotations
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional
from uuid import uuid4


@dataclass
class ActionContext:
    """Context information for a single action."""
    action_id: str = field(default_factory=lambda: str(uuid4())[:8])
    action_name: str = ""
    element_name: Optional[str] = None
    window_name: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_context: Optional[ActionContext] = None
    
    @property
    def description(self) -> str:
        """Generate a human-readable description of this action."""
        parts = [self.action_name]
        if self.element_name:
            parts.append(f"on '{self.element_name}'")
        if self.window_name:
            parts.append(f"in window '{self.window_name}'")
        return " ".join(parts)
    
    @property
    def elapsed_time(self) -> float:
        """Time elapsed since action started."""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "action_id": self.action_id,
            "action_name": self.action_name,
            "element_name": self.element_name,
            "window_name": self.window_name,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
        }
    
    def get_full_trace(self) -> List[ActionContext]:
        """Get the full chain of parent contexts."""
        trace = [self]
        current = self.parent_context
        while current is not None:
            trace.append(current)
            current = current.parent_context
        return trace
    
    def format_trace(self) -> str:
        """Format the full action trace for error messages."""
        trace = self.get_full_trace()
        lines = ["Action trace (most recent first):"]
        for i, ctx in enumerate(trace):
            prefix = "  -> " if i > 0 else "  X "
            lines.append(f"{prefix}{ctx.description} [{ctx.elapsed_time:.2f}s]")
        return "\n".join(lines)


class ActionContextManager:
    """Thread-safe manager for action context stack."""
    
    _local = threading.local()
    
    @classmethod
    def _get_stack(cls) -> List[ActionContext]:
        """Get the context stack for the current thread."""
        if not hasattr(cls._local, 'stack'):
            cls._local.stack = []
        return cls._local.stack
    
    @classmethod
    def current(cls) -> Optional[ActionContext]:
        """Get the current (innermost) action context."""
        stack = cls._get_stack()
        return stack[-1] if stack else None
    
    @classmethod
    def push(cls, context: ActionContext) -> None:
        """Push a new context onto the stack."""
        stack = cls._get_stack()
        if stack:
            context.parent_context = stack[-1]
        stack.append(context)
    
    @classmethod
    def pop(cls) -> Optional[ActionContext]:
        """Pop the current context from the stack."""
        stack = cls._get_stack()
        return stack.pop() if stack else None
    
    @classmethod
    @contextmanager
    def action(
        cls,
        action_name: str,
        element_name: Optional[str] = None,
        window_name: Optional[str] = None,
        **metadata: Any
    ) -> Generator[ActionContext, None, None]:
        """Context manager for tracking an action."""
        context = ActionContext(
            action_name=action_name,
            element_name=element_name,
            window_name=window_name,
            metadata=metadata
        )
        cls.push(context)
        try:
            yield context
        finally:
            cls.pop()
    
    @classmethod
    def get_current_description(cls) -> str:
        """Get description of current action, or default."""
        current = cls.current()
        if current:
            return current.description
        return "operation"
    
    @classmethod
    def clear(cls) -> None:
        """Clear the context stack (useful for test cleanup)."""
        cls._local.stack = []


def tracked_action(action_name: Optional[str] = None):
    """Decorator to automatically track action context."""
    def decorator(func):
        name = action_name or func.__name__
        
        def wrapper(*args, **kwargs):
            from .actionlogger import ACTION_LOGGER

            element_name = kwargs.get('element_name') or kwargs.get('element') or kwargs.get('name')
            if element_name is None and len(args) > 1:
                candidate = args[1]
                if isinstance(candidate, str):
                    element_name = candidate
            
            start_time = time.time()
            with ActionContextManager.action(name, element_name=element_name) as context:
                try:
                    result = func(*args, **kwargs)
                    duration_ms = int((time.time() - start_time) * 1000)
                    ACTION_LOGGER.log(
                        action=name,
                        element=element_name,
                        status="ok",
                        duration_ms=duration_ms,
                        metadata=kwargs,
                        action_id=context.action_id,
                        phase="execute",
                        event="action_finish",
                    )
                    return result
                except Exception as exc:
                    duration_ms = int((time.time() - start_time) * 1000)
                    ACTION_LOGGER.log(
                        action=name,
                        element=element_name,
                        status="error",
                        duration_ms=duration_ms,
                        metadata=kwargs,
                        exception=exc,
                        action_id=context.action_id,
                        phase="execute",
                        event="action_finish",
                    )
                    raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator