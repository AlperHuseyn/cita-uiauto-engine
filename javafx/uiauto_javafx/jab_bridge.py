# javafx/uiauto_javafx/jab_bridge.py
"""Java Access Bridge wrapper for JavaFX element access."""

from __future__ import annotations
import logging
from typing import Any, List, Optional, Dict

try:
    import jpype
    import jpype.imports
    from jpype.types import JInt, JString
    JPYPE_AVAILABLE = True
except ImportError:
    JPYPE_AVAILABLE = False
    jpype = None


class JABBridge:
    """
    Java Access Bridge wrapper for JavaFX element access.
    
    Provides Python interface to Java Accessibility API for UI automation.
    """
    
    def __init__(self, jvm_path: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize JAB bridge and start JVM if needed.
        
        Args:
            jvm_path: Optional path to JVM (uses default if not provided)
            logger: Optional logger instance
        """
        if not JPYPE_AVAILABLE:
            raise ImportError(
                "JPype1 is required for JavaFX automation. "
                "Install with: pip install JPype1"
            )
        
        self.log = logger or logging.getLogger("uiauto_javafx.jab_bridge")
        self.jvm_path = jvm_path or jpype.getDefaultJVMPath()
        self._init_jvm()
    
    def _init_jvm(self):
        """Initialize JVM with accessibility support."""
        if jpype.isJVMStarted():
            self.log.info("JVM already started")
            return
        
        self.log.info(f"Starting JVM: {self.jvm_path}")
        jpype.startJVM(
            self.jvm_path,
            "-Djava.awt.headless=false",
            "-Djavax.accessibility.assistive_technologies=",
            classpath=[],
        )
        
        # Import Java classes
        from javax.accessibility import AccessibleContext, AccessibleRole, AccessibleState
        from java.awt import Component, Window
        from java.awt.event import WindowEvent
        
        self.AccessibleContext = AccessibleContext
        self.AccessibleRole = AccessibleRole
        self.AccessibleState = AccessibleState
        self.Component = Component
        self.Window = Window
        self.WindowEvent = WindowEvent
        
        self.log.info("JVM started successfully")
    
    def shutdown(self):
        """Shutdown JVM (note: JVM cannot be restarted in same process)."""
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
            self.log.info("JVM shut down")
    
    def get_all_windows(self) -> List[Any]:
        """
        Get all accessible windows.
        
        Returns:
            List of Window objects
        """
        from java.awt import Window
        windows = []
        try:
            all_windows = Window.getWindows()
            for w in all_windows:
                if w and w.isVisible():
                    windows.append(w)
        except Exception as e:
            self.log.warning(f"Failed to get windows: {e}")
        return windows
    
    def get_window_by_title(self, title: str, exact: bool = False) -> Optional[Any]:
        """
        Find window by title.
        
        Args:
            title: Window title to search for
            exact: If True, match exact title; if False, match substring
            
        Returns:
            Window object or None
        """
        windows = self.get_all_windows()
        for w in windows:
            try:
                w_title = str(w.getTitle()) if hasattr(w, 'getTitle') else str(w.getName())
                if exact:
                    if w_title == title:
                        return w
                else:
                    if title in w_title:
                        return w
            except Exception as e:
                self.log.debug(f"Error getting window title: {e}")
        return None
    
    def get_accessible_context(self, component: Any) -> Optional[Any]:
        """
        Get AccessibleContext from a component.
        
        Args:
            component: AWT/Swing component
            
        Returns:
            AccessibleContext or None
        """
        try:
            if hasattr(component, 'getAccessibleContext'):
                return component.getAccessibleContext()
        except Exception as e:
            self.log.debug(f"Failed to get AccessibleContext: {e}")
        return None
    
    def find_elements_by_role(self, root_context: Any, role: str, max_depth: int = 10) -> List[Any]:
        """
        Find all elements with specified accessible role.
        
        Args:
            root_context: Root AccessibleContext to search from
            role: Accessible role name (e.g., "PUSH_BUTTON", "TEXT")
            max_depth: Maximum recursion depth
            
        Returns:
            List of AccessibleContext objects matching role
        """
        results = []
        self._traverse_tree(root_context, lambda ctx: self._role_matcher(ctx, role, results), max_depth)
        return results
    
    def find_element_by_name(self, root_context: Any, name: str, max_depth: int = 10) -> Optional[Any]:
        """
        Find first element with specified accessible name.
        
        Args:
            root_context: Root AccessibleContext to search from
            name: Accessible name to match
            max_depth: Maximum recursion depth
            
        Returns:
            AccessibleContext or None
        """
        result = [None]
        
        def matcher(ctx):
            try:
                ctx_name = ctx.getAccessibleName()
                if ctx_name and str(ctx_name) == name:
                    result[0] = ctx
                    return True  # Stop traversal
            except Exception:
                pass
            return False
        
        self._traverse_tree(root_context, matcher, max_depth)
        return result[0]
    
    def find_element_by_name_and_role(self, root_context: Any, name: str, role: str, max_depth: int = 10) -> Optional[Any]:
        """
        Find first element matching both name and role.
        
        Args:
            root_context: Root AccessibleContext to search from
            name: Accessible name to match
            role: Accessible role to match
            max_depth: Maximum recursion depth
            
        Returns:
            AccessibleContext or None
        """
        result = [None]
        
        def matcher(ctx):
            try:
                ctx_name = ctx.getAccessibleName()
                ctx_role = str(ctx.getAccessibleRole())
                if ctx_name and str(ctx_name) == name and ctx_role == role:
                    result[0] = ctx
                    return True
            except Exception:
                pass
            return False
        
        self._traverse_tree(root_context, matcher, max_depth)
        return result[0]
    
    def _traverse_tree(self, context: Any, visitor, max_depth: int, current_depth: int = 0):
        """
        Traverse accessibility tree depth-first.
        
        Args:
            context: Current AccessibleContext
            visitor: Callable(context) -> bool (return True to stop traversal)
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
        """
        if not context or current_depth >= max_depth:
            return
        
        try:
            # Visit current node
            if visitor(context):
                return  # Stop traversal
            
            # Visit children
            child_count = context.getAccessibleChildrenCount()
            for i in range(child_count):
                try:
                    child = context.getAccessibleChild(i)
                    if child:
                        child_context = child.getAccessibleContext()
                        if child_context:
                            self._traverse_tree(child_context, visitor, max_depth, current_depth + 1)
                except Exception as e:
                    self.log.debug(f"Error accessing child {i}: {e}")
        except Exception as e:
            self.log.debug(f"Error traversing tree: {e}")
    
    def _role_matcher(self, context: Any, role: str, results: List[Any]):
        """Helper to match role and collect results."""
        try:
            ctx_role = str(context.getAccessibleRole())
            if ctx_role == role:
                results.append(context)
        except Exception:
            pass
        return False  # Continue traversal
    
    def get_element_info(self, context: Any) -> Dict[str, Any]:
        """
        Extract information from AccessibleContext.
        
        Args:
            context: AccessibleContext to inspect
            
        Returns:
            Dict with element information
        """
        info = {
            "name": None,
            "role": None,
            "description": None,
            "text": None,
            "visible": False,
            "enabled": False,
            "child_count": 0,
        }
        
        try:
            info["name"] = str(context.getAccessibleName()) if context.getAccessibleName() else None
            info["role"] = str(context.getAccessibleRole())
            info["description"] = str(context.getAccessibleDescription()) if context.getAccessibleDescription() else None
            info["child_count"] = context.getAccessibleChildrenCount()
            
            # Get state
            state_set = context.getAccessibleStateSet()
            if state_set:
                info["visible"] = state_set.contains(self.AccessibleState.VISIBLE)
                info["enabled"] = state_set.contains(self.AccessibleState.ENABLED)
            
            # Try to get text
            accessible_text = context.getAccessibleText()
            if accessible_text:
                try:
                    char_count = accessible_text.getCharCount()
                    if char_count > 0:
                        info["text"] = str(accessible_text.getAtIndex(1, 0, char_count))  # Get all text
                except Exception:
                    pass
        except Exception as e:
            self.log.debug(f"Error getting element info: {e}")
        
        return info
    
    def map_control_type_to_role(self, control_type: str) -> str:
        """
        Map generic control type to Java AccessibleRole.
        
        Args:
            control_type: Generic control type (e.g., "Button", "Edit")
            
        Returns:
            Java AccessibleRole constant name
        """
        mapping = {
            "Button": "PUSH_BUTTON",
            "Edit": "TEXT",
            "Text": "LABEL",
            "ComboBox": "COMBO_BOX",
            "List": "LIST",
            "CheckBox": "CHECK_BOX",
            "RadioButton": "RADIO_BUTTON",
            "TabControl": "PAGE_TAB_LIST",
            "Tab": "PAGE_TAB",
            "Tree": "TREE",
            "Table": "TABLE",
            "MenuItem": "MENU_ITEM",
            "Menu": "MENU",
            "Window": "FRAME",
            "Dialog": "DIALOG",
            "ToolBar": "TOOL_BAR",
            "StatusBar": "STATUS_BAR",
            "ScrollBar": "SCROLL_BAR",
            "Pane": "PANEL",
        }
        return mapping.get(control_type, control_type.upper().replace(" ", "_"))
