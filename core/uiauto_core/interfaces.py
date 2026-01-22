"""
@file interfaces.py
@brief Abstract base classes for UI automation framework.

Defines interfaces that framework-specific implementations must implement,
enabling support for multiple UI frameworks (QtQuick, JavaFX, etc.) with
a common API.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ISession(ABC):
    """
    Abstract session interface for application lifecycle management.
    
    Handles starting applications, connecting to existing processes,
    acquiring windows, and cleanup operations.
    """
    
    @abstractmethod
    def start(self, app_path: str, **kwargs) -> int:
        """
        Start an application.
        
        Args:
            app_path: Path to application executable
            **kwargs: Framework-specific options (wait_for_idle, cmd_line, etc.)
            
        Returns:
            Process ID of started application
        """
        pass
    
    @abstractmethod
    def connect(self, **kwargs) -> None:
        """
        Connect to an existing application.
        
        Args:
            **kwargs: Connection parameters (pid, handle, title, etc.)
        """
        pass
    
    @abstractmethod
    def get_window(self, window_name: str, **locators) -> Any:
        """
        Get a window handle by name or locators.
        
        Args:
            window_name: Semantic window name
            **locators: Framework-specific window locators
            
        Returns:
            Framework-specific window handle
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Close application gracefully.
        """
        pass


class IResolver(ABC):
    """
    Abstract resolver interface for element resolution.
    
    Resolves semantic element names from object maps to actual
    UI elements using framework-specific locator strategies.
    """
    
    @abstractmethod
    def resolve_window(self, window_name: str) -> Any:
        """
        Resolve window by semantic name.
        
        Args:
            window_name: Window name from object map
            
        Returns:
            Framework-specific window handle
        """
        pass
    
    @abstractmethod
    def resolve(self, element_name: str, overrides: Optional[Dict[str, Any]] = None) -> "IElement":
        """
        Resolve element by semantic name.
        
        Args:
            element_name: Element name from object map
            overrides: Optional locator overrides for runtime customization
            
        Returns:
            IElement wrapper for resolved element
        """
        pass


class IElement(ABC):
    """
    Abstract element interface for UI interaction.
    
    Provides common operations for UI elements with framework-agnostic API.
    """
    
    @abstractmethod
    def click(self) -> None:
        """Click the element."""
        pass
    
    @abstractmethod
    def type_keys(self, text: str, clear_first: bool = True) -> None:
        """
        Type text into the element.
        
        Args:
            text: Text to type
            clear_first: Clear existing text before typing
        """
        pass
    
    @abstractmethod
    def get_text(self) -> str:
        """
        Get text from the element.
        
        Returns:
            Element text content
        """
        pass
    
    @abstractmethod
    def is_visible(self) -> bool:
        """
        Check if element is visible.
        
        Returns:
            True if visible, False otherwise
        """
        pass
    
    @abstractmethod
    def wait(self, state: str, timeout: Optional[float] = None) -> "IElement":
        """
        Wait for element to reach specified state.
        
        Args:
            state: State to wait for ("exists", "visible", "enabled")
            timeout: Timeout in seconds (uses default if None)
            
        Returns:
            Self for method chaining
        """
        pass


class IInspector(ABC):
    """
    Abstract inspector interface for UI tree inspection.
    
    Inspects UI hierarchy and generates object maps for element identification.
    """
    
    @abstractmethod
    def inspect_window(self, **criteria) -> Dict[str, Any]:
        """
        Inspect window and return UI tree structure.
        
        Args:
            **criteria: Window identification criteria
            
        Returns:
            Dictionary containing UI tree metadata and controls
        """
        pass
    
    @abstractmethod
    def emit_elements_yaml(self, result: Dict[str, Any], out_path: str, **kwargs) -> str:
        """
        Generate elements.yaml object map from inspection results.
        
        Args:
            result: Inspection result from inspect_window
            out_path: Output file path
            **kwargs: Framework-specific options (window_name, state, etc.)
            
        Returns:
            Path to generated YAML file
        """
        pass


class IActions(ABC):
    """
    Abstract actions interface for high-level keyword operations.
    
    Provides keyword-driven actions that resolve elements and perform
    common UI automation tasks with consistent error handling.
    """
    
    @abstractmethod
    def click(self, element: str, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        Click an element.
        
        Args:
            element: Element name from object map
            overrides: Optional locator overrides
        """
        pass
    
    @abstractmethod
    def type(self, element: str, text: str, overrides: Optional[Dict[str, Any]] = None, clear: bool = True) -> None:
        """
        Type text into an element.
        
        Args:
            element: Element name from object map
            text: Text to type
            overrides: Optional locator overrides
            clear: Clear existing text before typing
        """
        pass
    
    @abstractmethod
    def wait_for(self, element: str, state: str = "visible", timeout: Optional[float] = None, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        Wait for element to reach specified state.
        
        Args:
            element: Element name from object map
            state: State to wait for ("exists", "visible", "enabled")
            timeout: Timeout in seconds
            overrides: Optional locator overrides
        """
        pass
