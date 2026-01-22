# core/uiauto_core/interfaces.py
"""
Abstract base classes defining the interfaces for UI automation framework implementations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List


class ISession(ABC):
    """Abstract session interface for managing application lifecycle."""
    
    @abstractmethod
    def start(self, app_path: str, **kwargs) -> int:
        """
        Start an application.
        
        @param app_path Path to application executable
        @param kwargs Additional platform-specific arguments
        @return Process ID of started application
        """
        pass
    
    @abstractmethod
    def connect(self, **kwargs) -> None:
        """
        Connect to an existing application.
        
        @param kwargs Connection parameters (process, handle, title, etc.)
        """
        pass
    
    @abstractmethod
    def desktop_window(self, **kwargs) -> Any:
        """
        Get a top-level window from desktop.
        
        @param kwargs Window search parameters
        @return Window object
        """
        pass
    
    @abstractmethod
    def app_window(self, **kwargs) -> Any:
        """
        Get a window from connected/started application.
        
        @param kwargs Window search parameters
        @return Window object
        """
        pass
    
    @abstractmethod
    def close_main_windows(self, timeout: float = 5.0) -> None:
        """
        Close all main windows of the application.
        
        @param timeout Timeout for close operation
        """
        pass
    
    @abstractmethod
    def kill(self) -> None:
        """Force kill the application process."""
        pass


class IElement(ABC):
    """Abstract element interface for UI element interactions."""
    
    @abstractmethod
    def exists(self) -> bool:
        """Check if element exists in UI tree."""
        pass
    
    @abstractmethod
    def is_visible(self) -> bool:
        """Check if element is visible."""
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if element is enabled/interactive."""
        pass
    
    @abstractmethod
    def wait(self, state: str = "exists", timeout: Optional[float] = None) -> "IElement":
        """
        Wait for element to reach specified state.
        
        @param state State to wait for: "exists", "visible", "enabled"
        @param timeout Timeout in seconds
        @return Self for chaining
        """
        pass
    
    @abstractmethod
    def click(self, **kwargs) -> None:
        """Click the element."""
        pass
    
    @abstractmethod
    def double_click(self, **kwargs) -> None:
        """Double-click the element."""
        pass
    
    @abstractmethod
    def right_click(self, **kwargs) -> None:
        """Right-click the element."""
        pass
    
    @abstractmethod
    def hover(self) -> None:
        """Hover mouse over the element."""
        pass
    
    @abstractmethod
    def set_text(self, text: str, clear_first: bool = False) -> None:
        """
        Set text in the element.
        
        @param text Text to set
        @param clear_first Clear existing text before setting
        """
        pass
    
    @abstractmethod
    def type_keys(self, keys: str, **kwargs) -> None:
        """
        Type keys into the element.
        
        @param keys Keys to type
        @param kwargs Additional typing parameters
        """
        pass
    
    @abstractmethod
    def get_text(self) -> str:
        """Get text from the element."""
        pass
    
    @abstractmethod
    def focus(self) -> None:
        """Set focus to the element."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear text from the element."""
        pass


class IResolver(ABC):
    """Abstract resolver interface for element resolution."""
    
    @abstractmethod
    def resolve_window(self, window_name: str) -> Any:
        """
        Resolve window by semantic name.
        
        @param window_name Window name from object map
        @return Window object
        """
        pass
    
    @abstractmethod
    def resolve(self, element_name: str, overrides: Optional[Dict[str, Any]] = None) -> IElement:
        """
        Resolve element by semantic name.
        
        @param element_name Element name from object map
        @param overrides Optional locator overrides
        @return Element wrapper
        """
        pass
