# javafx/uiauto_javafx/jab_bridge.py
"""
Java Access Bridge wrapper for JavaFX element access.

This module provides a Python interface to the Java Access Bridge (JAB),
allowing automation of JavaFX applications via the Java Accessibility API.
"""
from __future__ import annotations
import time
import logging
from typing import Any, List, Optional, Dict

try:
    import jpype
    import jpype.imports
    from jpype.types import JInt, JBoolean
except ImportError:
    raise ImportError("JPype1 is required for JavaFX automation. Install with: pip install JPype1")


class JABBridge:
    """
    Java Access Bridge wrapper for JavaFX element access.
    
    Provides Python interface to Java Accessibility API for finding and
    interacting with JavaFX UI elements.
    """
    
    def __init__(self, jvm_path: Optional[str] = None, log: Optional[logging.Logger] = None):
        """
        Initialize JAB bridge and start JVM if needed.
        
        @param jvm_path Optional path to JVM library
        @param log Optional logger instance
        """
        self.jvm_path = jvm_path or jpype.getDefaultJVMPath()
        self.log = log or logging.getLogger("uiauto.javafx")
        self._init_jvm()
    
    def _init_jvm(self):
        """Initialize JVM with accessibility support."""
        if not jpype.isJVMStarted():
            self.log.info("Starting JVM with accessibility support")
            try:
                jpype.startJVM(
                    self.jvm_path,
                    "-Djavax.accessibility.assistive_technologies=",  # Empty to avoid issues
                    "-Djava.awt.headless=false",
                    convertStrings=False
                )
            except Exception as e:
                self.log.error(f"Failed to start JVM: {e}")
                raise
        
        # Import Java classes
        try:
            import javax.accessibility as accessibility
            import java.awt as awt
            
            self.AccessibleContext = accessibility.AccessibleContext
            self.AccessibleRole = accessibility.AccessibleRole
            self.AccessibleState = accessibility.AccessibleState
            self.Component = awt.Component
            self.log.info("JAB initialized successfully")
        except Exception as e:
            self.log.error(f"Failed to import Java accessibility classes: {e}")
            raise
    
    def find_window_by_title(self, title: str, exact: bool = False) -> Optional[Any]:
        """
        Find window by title.
        
        @param title Window title to search for
        @param exact If True, require exact match; if False, use substring match
        @return Window AccessibleContext or None
        """
        # Note: This is a simplified implementation
        # Real implementation would need to use Java Access Bridge native APIs
        # to enumerate top-level windows
        self.log.warning("find_window_by_title: Simplified implementation - may not work for all cases")
        return None
    
    def get_accessible_context_from_point(self, x: int, y: int) -> Optional[Any]:
        """
        Get AccessibleContext at screen coordinates.
        
        @param x Screen X coordinate
        @param y Screen Y coordinate
        @return AccessibleContext or None
        """
        # This would require native JAB APIs
        self.log.warning("get_accessible_context_from_point: Not yet implemented")
        return None
    
    def find_elements_by_role(self, root: Any, role: str, max_depth: int = 10) -> List[Any]:
        """
        Find elements by accessible role in tree.
        
        @param root Root AccessibleContext to search from
        @param role Accessible role name (e.g., "PUSH_BUTTON", "TEXT")
        @param max_depth Maximum tree depth to traverse
        @return List of matching AccessibleContexts
        """
        if root is None:
            return []
        
        results = []
        
        def traverse(ctx, depth: int):
            if depth > max_depth or ctx is None:
                return
            
            try:
                ctx_role = ctx.getAccessibleRole()
                if ctx_role and str(ctx_role).upper() == role.upper():
                    results.append(ctx)
                
                # Traverse children
                child_count = ctx.getAccessibleChildrenCount()
                for i in range(child_count):
                    child = ctx.getAccessibleChild(i)
                    if child:
                        child_ctx = child.getAccessibleContext()
                        if child_ctx:
                            traverse(child_ctx, depth + 1)
            except Exception as e:
                self.log.debug(f"Error traversing node at depth {depth}: {e}")
        
        traverse(root, 0)
        return results
    
    def find_element_by_name(self, root: Any, name: str, max_depth: int = 10) -> Optional[Any]:
        """
        Find element by accessibleName.
        
        @param root Root AccessibleContext to search from
        @param name Accessible name to match
        @param max_depth Maximum tree depth to traverse
        @return AccessibleContext or None
        """
        if root is None:
            return None
        
        def traverse(ctx, depth: int) -> Optional[Any]:
            if depth > max_depth or ctx is None:
                return None
            
            try:
                ctx_name = ctx.getAccessibleName()
                if ctx_name and str(ctx_name) == name:
                    return ctx
                
                # Traverse children
                child_count = ctx.getAccessibleChildrenCount()
                for i in range(child_count):
                    child = ctx.getAccessibleChild(i)
                    if child:
                        child_ctx = child.getAccessibleContext()
                        if child_ctx:
                            result = traverse(child_ctx, depth + 1)
                            if result:
                                return result
            except Exception as e:
                self.log.debug(f"Error traversing node at depth {depth}: {e}")
            
            return None
        
        return traverse(root, 0)
    
    def find_element_by_name_and_role(
        self, 
        root: Any, 
        name: str, 
        role: str,
        max_depth: int = 10
    ) -> Optional[Any]:
        """
        Find element by accessibleName and role.
        
        @param root Root AccessibleContext to search from
        @param name Accessible name to match
        @param role Accessible role to match
        @param max_depth Maximum tree depth to traverse
        @return AccessibleContext or None
        """
        if root is None:
            return None
        
        def traverse(ctx, depth: int) -> Optional[Any]:
            if depth > max_depth or ctx is None:
                return None
            
            try:
                ctx_name = ctx.getAccessibleName()
                ctx_role = ctx.getAccessibleRole()
                
                if (ctx_name and str(ctx_name) == name and 
                    ctx_role and str(ctx_role).upper() == role.upper()):
                    return ctx
                
                # Traverse children
                child_count = ctx.getAccessibleChildrenCount()
                for i in range(child_count):
                    child = ctx.getAccessibleChild(i)
                    if child:
                        child_ctx = child.getAccessibleContext()
                        if child_ctx:
                            result = traverse(child_ctx, depth + 1)
                            if result:
                                return result
            except Exception as e:
                self.log.debug(f"Error traversing node at depth {depth}: {e}")
            
            return None
        
        return traverse(root, 0)
    
    def get_element_info(self, ctx: Any) -> Dict[str, Any]:
        """
        Get detailed information about an accessible element.
        
        @param ctx AccessibleContext
        @return Dict with element properties
        """
        info = {
            "name": None,
            "description": None,
            "role": None,
            "states": [],
            "visible": False,
            "enabled": False,
            "focusable": False,
            "child_count": 0,
        }
        
        if ctx is None:
            return info
        
        try:
            info["name"] = str(ctx.getAccessibleName()) if ctx.getAccessibleName() else None
            info["description"] = str(ctx.getAccessibleDescription()) if ctx.getAccessibleDescription() else None
            info["role"] = str(ctx.getAccessibleRole()) if ctx.getAccessibleRole() else None
            info["child_count"] = ctx.getAccessibleChildrenCount()
            
            # Get states
            state_set = ctx.getAccessibleStateSet()
            if state_set:
                from javax.accessibility import AccessibleState
                info["visible"] = state_set.contains(AccessibleState.VISIBLE)
                info["enabled"] = state_set.contains(AccessibleState.ENABLED)
                info["focusable"] = state_set.contains(AccessibleState.FOCUSABLE)
                
                # Collect all states
                states = []
                for state in [AccessibleState.VISIBLE, AccessibleState.ENABLED, 
                             AccessibleState.FOCUSABLE, AccessibleState.FOCUSED,
                             AccessibleState.SELECTED, AccessibleState.SHOWING]:
                    if state_set.contains(state):
                        states.append(str(state))
                info["states"] = states
        except Exception as e:
            self.log.debug(f"Error getting element info: {e}")
        
        return info
    
    def shutdown(self):
        """Shutdown JVM (use with caution - cannot restart in same process)."""
        if jpype.isJVMStarted():
            self.log.info("Shutting down JVM")
            jpype.shutdownJVM()
