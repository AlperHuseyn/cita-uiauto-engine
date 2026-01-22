# core/uiauto_core/interfaces.py
"""Abstract base classes for framework-agnostic UI automation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ISession(ABC):
    """Abstract session interface for UI automation framework connections."""
    
    @abstractmethod
    def start(self, app_path: str, **kwargs) -> int:
        """
        Start an application.
        
        Args:
            app_path: Path to application executable
            **kwargs: Additional framework-specific arguments
            
        Returns:
            Process ID of started application
        """
        pass
    
    @abstractmethod
    def connect(self, **kwargs) -> None:
        """
        Connect to an existing application.
        
        Args:
            **kwargs: Framework-specific connection parameters (e.g., process=, handle=)
        """
        pass
    
    @abstractmethod
    def desktop_window(self, **kwargs) -> Any:
        """
        Get a top-level window from desktop.
        
        Args:
            **kwargs: Framework-specific window locators
            
        Returns:
            Window object
        """
        pass
    
    @abstractmethod
    def app_window(self, **kwargs) -> Any:
        """
        Get a window from connected application.
        
        Args:
            **kwargs: Framework-specific window locators
            
        Returns:
            Window object
        """
        pass
    
    @abstractmethod
    def close_main_windows(self, timeout: float = 5.0) -> None:
        """
        Close all main windows of the application.
        
        Args:
            timeout: Timeout in seconds
        """
        pass
    
    @abstractmethod
    def kill(self) -> None:
        """Force kill the application process."""
        pass


class IResolver(ABC):
    """Abstract resolver interface for element resolution."""
    
    @abstractmethod
    def resolve_window(self, window_name: str) -> Any:
        """
        Resolve a window by its semantic name from the repository.
        
        Args:
            window_name: Window name from object map
            
        Returns:
            Window object
        """
        pass
    
    @abstractmethod
    def resolve(self, element_name: str, overrides: Optional[Dict[str, Any]] = None) -> "IElement":
        """
        Resolve an element by its semantic name from the repository.
        
        Args:
            element_name: Element name from object map
            overrides: Optional locator overrides
            
        Returns:
            IElement instance
        """
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
        """Check if element is enabled."""
        pass
    
    @abstractmethod
    def wait(self, state: str = "exists", timeout: Optional[float] = None) -> "IElement":
        """
        Wait for element to reach specified state.
        
        Args:
            state: State to wait for ("exists", "visible", "enabled")
            timeout: Timeout in seconds
            
        Returns:
            Self for chaining
        """
        pass
    
    @abstractmethod
    def click(self, **kwargs) -> None:
        """Click element."""
        pass
    
    @abstractmethod
    def double_click(self, **kwargs) -> None:
        """Double-click element."""
        pass
    
    @abstractmethod
    def right_click(self, **kwargs) -> None:
        """Right-click element."""
        pass
    
    @abstractmethod
    def hover(self) -> None:
        """Hover mouse over element."""
        pass
    
    @abstractmethod
    def set_text(self, text: str, clear_first: bool = False) -> None:
        """
        Set text in element.
        
        Args:
            text: Text to set
            clear_first: Clear existing text first
        """
        pass
    
    @abstractmethod
    def type_keys(self, keys: str, **kwargs) -> None:
        """
        Type keys into element.
        
        Args:
            keys: Keys to type
            **kwargs: Framework-specific options
        """
        pass
    
    @abstractmethod
    def get_text(self) -> str:
        """Get text from element."""
        pass
    
    @abstractmethod
    def focus(self) -> None:
        """Set focus to element."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear text from element."""
        pass
