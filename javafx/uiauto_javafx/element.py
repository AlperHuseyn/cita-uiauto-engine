# javafx/uiauto_javafx/element.py
"""JavaFX element wrapper using Java Access Bridge."""

from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from uiauto_core.interfaces import IElement
from uiauto_core.waits import wait_until


@dataclass
class ElementMeta:
    """Metadata for resolved JavaFX element."""
    name: str
    window_name: str
    used_locator: Dict[str, Any]
    found_via_name: bool = False


class JavaFXElement(IElement):
    """
    JavaFX element wrapper using AccessibleContext.
    
    Provides interaction methods using Java Accessibility API.
    """
    
    def __init__(self, accessible_context: Any, meta: ElementMeta, default_timeout: float, polling_interval: float):
        """
        Initialize JavaFX element.
        
        Args:
            accessible_context: Java AccessibleContext object
            meta: Element metadata
            default_timeout: Default timeout for waits
            polling_interval: Polling interval for waits
        """
        self.context = accessible_context
        self.meta = meta
        self.default_timeout = default_timeout
        self.polling_interval = polling_interval
    
    def exists(self) -> bool:
        """Check if element still exists in accessibility tree."""
        try:
            # Try to access a property to verify context is valid
            _ = self.context.getAccessibleName()
            return True
        except Exception:
            return False
    
    def is_visible(self) -> bool:
        """Check if element is visible."""
        try:
            state_set = self.context.getAccessibleStateSet()
            if state_set:
                from javax.accessibility import AccessibleState
                return state_set.contains(AccessibleState.VISIBLE)
        except Exception:
            pass
        return False
    
    def is_enabled(self) -> bool:
        """Check if element is enabled."""
        try:
            state_set = self.context.getAccessibleStateSet()
            if state_set:
                from javax.accessibility import AccessibleState
                return state_set.contains(AccessibleState.ENABLED)
        except Exception:
            pass
        return False
    
    def wait(self, state: str = "exists", timeout: Optional[float] = None) -> "JavaFXElement":
        """
        Wait for element to reach specified state.
        
        Args:
            state: State to wait for ("exists", "visible", "enabled")
            timeout: Timeout in seconds
            
        Returns:
            Self for chaining
        """
        timeout = self.default_timeout if timeout is None else float(timeout)
        
        def pred():
            if state == "exists":
                return self.exists()
            if state == "visible":
                return self.exists() and self.is_visible()
            if state == "enabled":
                return self.exists() and self.is_visible() and self.is_enabled()
            raise ValueError(f"Unknown wait state: {state}")
        
        wait_until(pred, timeout=timeout, interval=self.polling_interval,
                   description=f"{self.meta.name} to be {state}")
        return self
    
    def click(self, **kwargs) -> None:
        """
        Click element using AccessibleAction.
        
        Args:
            **kwargs: Additional options (ignored for now)
        """
        try:
            # Get accessible action interface
            action = self.context.getAccessibleAction()
            if action and action.getAccessibleActionCount() > 0:
                # Perform default action (usually index 0)
                action.doAccessibleAction(0)
                time.sleep(0.1)  # Brief pause after click
            else:
                raise RuntimeError("Element does not support actions")
        except Exception as e:
            raise RuntimeError(f"Click failed on {self.meta.name}: {e}")
    
    def double_click(self, **kwargs) -> None:
        """
        Double-click element (two single clicks).
        
        Args:
            **kwargs: Additional options
        """
        self.click(**kwargs)
        time.sleep(0.05)
        self.click(**kwargs)
    
    def right_click(self, **kwargs) -> None:
        """
        Right-click element.
        
        Note: Java Accessibility API doesn't have native right-click support.
        This is a placeholder that raises an error.
        
        Args:
            **kwargs: Additional options
        """
        raise NotImplementedError("Right-click not supported via Java Accessibility API")
    
    def hover(self) -> None:
        """
        Hover over element.
        
        Note: Java Accessibility API doesn't have native hover support.
        This is a placeholder that raises an error.
        """
        raise NotImplementedError("Hover not supported via Java Accessibility API")
    
    def set_text(self, text: str, clear_first: bool = False) -> None:
        """
        Set text in element using AccessibleEditableText.
        
        Args:
            text: Text to set
            clear_first: Clear existing text first
        """
        try:
            editable_text = self.context.getAccessibleEditableText()
            if editable_text:
                if clear_first:
                    # Get current text length and delete all
                    accessible_text = self.context.getAccessibleText()
                    if accessible_text:
                        char_count = accessible_text.getCharCount()
                        if char_count > 0:
                            editable_text.delete(0, char_count)
                
                # Insert new text at position 0
                editable_text.insertTextAtIndex(0, text)
                return
            
            # Fallback: try to set text via AccessibleValue
            value = self.context.getAccessibleValue()
            if value:
                from java.lang import String
                value.setCurrentAccessibleValue(String(text))
                return
            
            raise RuntimeError("Element does not support text editing")
        except Exception as e:
            raise RuntimeError(f"Set text failed on {self.meta.name}: {e}")
    
    def type_keys(self, keys: str, **kwargs) -> None:
        """
        Type keys into element.
        
        Note: This uses set_text as a fallback. Robot-based key simulation
        would be needed for true key events.
        
        Args:
            keys: Text to type
            **kwargs: Additional options
        """
        self.set_text(keys, clear_first=False)
    
    def get_text(self) -> str:
        """
        Get text from element.
        
        Returns:
            Element text or empty string
        """
        try:
            # Try AccessibleText first
            accessible_text = self.context.getAccessibleText()
            if accessible_text:
                char_count = accessible_text.getCharCount()
                if char_count > 0:
                    # Get all text
                    text = accessible_text.getAtIndex(1, 0, char_count)  # SENTENCE level
                    return str(text) if text else ""
            
            # Try AccessibleValue
            value = self.context.getAccessibleValue()
            if value:
                current = value.getCurrentAccessibleValue()
                if current:
                    return str(current)
            
            # Fallback to AccessibleName
            name = self.context.getAccessibleName()
            if name:
                return str(name)
        except Exception:
            pass
        
        return ""
    
    def focus(self) -> None:
        """
        Set focus to element.
        
        Note: Java Accessibility API has limited focus control.
        This attempts to request focus via the component.
        """
        try:
            # Try to get the component and request focus
            component = self.context.getAccessibleComponent()
            if component:
                component.requestFocus()
        except Exception as e:
            raise RuntimeError(f"Focus failed on {self.meta.name}: {e}")
    
    def clear(self) -> None:
        """Clear text from element."""
        try:
            editable_text = self.context.getAccessibleEditableText()
            if editable_text:
                accessible_text = self.context.getAccessibleText()
                if accessible_text:
                    char_count = accessible_text.getCharCount()
                    if char_count > 0:
                        editable_text.delete(0, char_count)
                return
            
            # Fallback: set empty text
            self.set_text("", clear_first=True)
        except Exception as e:
            raise RuntimeError(f"Clear failed on {self.meta.name}: {e}")
    
    # Additional JavaFX-specific methods
    
    def get_role(self) -> str:
        """Get element's accessible role."""
        try:
            return str(self.context.getAccessibleRole())
        except Exception:
            return "UNKNOWN"
    
    def get_description(self) -> str:
        """Get element's accessible description."""
        try:
            desc = self.context.getAccessibleDescription()
            return str(desc) if desc else ""
        except Exception:
            return ""
    
    def get_child_count(self) -> int:
        """Get number of accessible children."""
        try:
            return self.context.getAccessibleChildrenCount()
        except Exception:
            return 0
