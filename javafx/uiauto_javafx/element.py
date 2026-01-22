# javafx/uiauto_javafx/element.py
"""JavaFX element wrapper using Java Access Bridge."""
from __future__ import annotations
import time
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from uiauto_core.interfaces import IElement
from uiauto_core.waits import wait_until


@dataclass
class JavaFXElementMeta:
    """Metadata for JavaFX element."""
    name: str
    window_name: str
    used_locator: Dict[str, Any]


class JavaFXElement(IElement):
    """
    JavaFX element wrapper using AccessibleContext.
    
    Provides UI automation operations via Java Accessibility API.
    """
    
    def __init__(
        self,
        accessible_context: Any,
        meta: JavaFXElementMeta,
        default_timeout: float = 10.0,
        polling_interval: float = 0.2,
    ):
        """
        Initialize JavaFX element wrapper.
        
        @param accessible_context Java AccessibleContext object
        @param meta Element metadata
        @param default_timeout Default timeout for operations
        @param polling_interval Polling interval for waits
        """
        self.context = accessible_context
        self.meta = meta
        self.default_timeout = default_timeout
        self.polling_interval = polling_interval
        self.log = logging.getLogger("uiauto.javafx")
    
    def exists(self) -> bool:
        """Check if element exists."""
        return self.context is not None
    
    def is_visible(self) -> bool:
        """Check if element is visible."""
        if not self.exists():
            return False
        
        try:
            from javax.accessibility import AccessibleState
            state_set = self.context.getAccessibleStateSet()
            if state_set:
                return state_set.contains(AccessibleState.VISIBLE)
        except Exception as e:
            self.log.debug(f"Error checking visibility: {e}")
        
        return False
    
    def is_enabled(self) -> bool:
        """Check if element is enabled."""
        if not self.exists():
            return False
        
        try:
            from javax.accessibility import AccessibleState
            state_set = self.context.getAccessibleStateSet()
            if state_set:
                return state_set.contains(AccessibleState.ENABLED)
        except Exception as e:
            self.log.debug(f"Error checking enabled state: {e}")
        
        return False
    
    def wait(self, state: str = "exists", timeout: Optional[float] = None) -> "JavaFXElement":
        """
        Wait for element to reach specified state.
        
        @param state State to wait for: "exists", "visible", "enabled"
        @param timeout Timeout in seconds
        @return Self for chaining
        """
        timeout = self.default_timeout if timeout is None else float(timeout)
        
        def pred():
            if state == "exists":
                return self.exists()
            elif state == "visible":
                return self.exists() and self.is_visible()
            elif state == "enabled":
                return self.exists() and self.is_visible() and self.is_enabled()
            else:
                raise ValueError(f"Unknown wait state: {state}")
        
        wait_until(
            pred,
            timeout=timeout,
            interval=self.polling_interval,
            description=f"{self.meta.name} to be {state}"
        )
        return self
    
    def click(self, **kwargs) -> None:
        """
        Click the element using AccessibleAction.
        """
        if not self.exists():
            raise RuntimeError(f"Element {self.meta.name} does not exist")
        
        try:
            actions = self.context.getAccessibleAction()
            if actions and actions.getAccessibleActionCount() > 0:
                # Typically, action 0 is the default action (click/activate)
                success = actions.doAccessibleAction(0)
                if not success:
                    raise RuntimeError("doAccessibleAction returned false")
                return
        except Exception as e:
            raise RuntimeError(f"Click failed on {self.meta.name}: {e}")
    
    def double_click(self, **kwargs) -> None:
        """
        Double-click the element (clicks twice with small delay).
        """
        self.click(**kwargs)
        time.sleep(0.1)
        self.click(**kwargs)
    
    def right_click(self, **kwargs) -> None:
        """
        Right-click the element.
        
        Note: JAB doesn't have native right-click support,
        this is a placeholder that logs a warning.
        """
        self.log.warning(f"Right-click not fully supported for {self.meta.name}")
        # Could potentially use Robot class for mouse events
    
    def hover(self) -> None:
        """
        Hover over the element.
        
        Note: JAB doesn't have native hover support,
        this is a placeholder that logs a warning.
        """
        self.log.warning(f"Hover not fully supported for {self.meta.name}")
        # Could potentially use Robot class for mouse events
    
    def set_text(self, text: str, clear_first: bool = False) -> None:
        """
        Set text in the element using AccessibleEditableText.
        
        @param text Text to set
        @param clear_first Whether to clear existing text first
        """
        if not self.exists():
            raise RuntimeError(f"Element {self.meta.name} does not exist")
        
        try:
            editable = self.context.getAccessibleEditableText()
            if editable:
                if clear_first:
                    # Get current length and delete all
                    accessible_text = self.context.getAccessibleText()
                    if accessible_text:
                        char_count = accessible_text.getCharCount()
                        if char_count > 0:
                            editable.delete(0, char_count)
                
                # Insert new text
                editable.insertTextAtIndex(0, text)
                return
        except Exception:
            pass
        
        # Fallback: try setTextContents if available
        try:
            editable = self.context.getAccessibleEditableText()
            if editable:
                editable.setTextContents(text)
                return
        except Exception as e:
            raise RuntimeError(f"Set text failed on {self.meta.name}: {e}")
    
    def type_keys(self, keys: str, **kwargs) -> None:
        """
        Type keys into the element.
        
        Note: This is a simplified implementation that just calls set_text.
        Full keyboard event simulation would require Java Robot class.
        
        @param keys Keys to type
        @param kwargs Additional parameters
        """
        self.set_text(keys, clear_first=False)
    
    def get_text(self) -> str:
        """Get text from the element."""
        if not self.exists():
            return ""
        
        try:
            # Try AccessibleText first
            accessible_text = self.context.getAccessibleText()
            if accessible_text:
                text = accessible_text.getWholeText()
                if text:
                    return str(text)
        except Exception:
            pass
        
        # Fallback to accessibleName
        try:
            name = self.context.getAccessibleName()
            if name:
                return str(name)
        except Exception:
            pass
        
        return ""
    
    def focus(self) -> None:
        """
        Set focus to the element.
        
        Note: Setting focus via JAB is limited.
        This tries to request focus if possible.
        """
        if not self.exists():
            raise RuntimeError(f"Element {self.meta.name} does not exist")
        
        try:
            # Try to get the Component and request focus
            component = self.context.getAccessibleComponent()
            if component:
                component.requestFocus()
                return
        except Exception as e:
            self.log.warning(f"Focus request failed on {self.meta.name}: {e}")
    
    def clear(self) -> None:
        """Clear text from the element."""
        self.set_text("", clear_first=True)
    
    def check(self) -> None:
        """Check a checkbox (idempotent)."""
        # Use AccessibleAction with toggle or check
        try:
            actions = self.context.getAccessibleAction()
            if actions:
                # Try to find "toggle" or "check" action
                count = actions.getAccessibleActionCount()
                for i in range(count):
                    desc = str(actions.getAccessibleActionDescription(i)).lower()
                    if "toggle" in desc or "check" in desc:
                        actions.doAccessibleAction(i)
                        return
                
                # Fallback: use first action
                if count > 0:
                    actions.doAccessibleAction(0)
        except Exception as e:
            raise RuntimeError(f"Check failed on {self.meta.name}: {e}")
    
    def uncheck(self) -> None:
        """Uncheck a checkbox (idempotent)."""
        # Similar to check - toggle action
        self.check()
    
    def toggle(self) -> None:
        """Toggle checkbox state."""
        self.check()
    
    def get_state(self) -> str:
        """Get checkbox state."""
        try:
            from javax.accessibility import AccessibleState
            state_set = self.context.getAccessibleStateSet()
            if state_set:
                if state_set.contains(AccessibleState.CHECKED):
                    return "checked"
                else:
                    return "unchecked"
        except Exception:
            pass
        
        return "unknown"
    
    def select(self, option: Any, by_index: bool = False) -> None:
        """Select option in combobox/list."""
        try:
            selection = self.context.getAccessibleSelection()
            if selection:
                if by_index:
                    selection.addAccessibleSelection(int(option))
                else:
                    # Find child by text
                    child_count = self.context.getAccessibleChildrenCount()
                    for i in range(child_count):
                        child = self.context.getAccessibleChild(i)
                        if child:
                            child_ctx = child.getAccessibleContext()
                            if child_ctx:
                                name = child_ctx.getAccessibleName()
                                if name and str(option) in str(name):
                                    selection.addAccessibleSelection(i)
                                    return
                return
        except Exception as e:
            raise RuntimeError(f"Select failed on {self.meta.name}: {e}")
    
    def expand(self) -> None:
        """Expand combobox."""
        self.click()
    
    def collapse(self) -> None:
        """Collapse combobox."""
        # Try pressing Escape (would need Robot)
        self.log.warning("Collapse not fully implemented")
    
    def item_texts(self) -> list:
        """Get list of item texts."""
        items = []
        try:
            child_count = self.context.getAccessibleChildrenCount()
            for i in range(child_count):
                child = self.context.getAccessibleChild(i)
                if child:
                    child_ctx = child.getAccessibleContext()
                    if child_ctx:
                        name = child_ctx.getAccessibleName()
                        if name:
                            items.append(str(name))
        except Exception:
            pass
        
        return items
    
    def select_item(self, item_text: str = None, item_index: int = None) -> None:
        """Select item in list."""
        if item_index is not None:
            self.select(item_index, by_index=True)
        elif item_text is not None:
            self.select(item_text, by_index=False)
    
    def item_count(self) -> int:
        """Get count of items."""
        try:
            return self.context.getAccessibleChildrenCount()
        except Exception:
            return 0
