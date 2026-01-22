# javafx/uiauto_javafx/session.py
"""JavaFX session implementation using Java Access Bridge."""

from __future__ import annotations
import logging
import subprocess
import time
from typing import Any, Optional, List

from uiauto_core.interfaces import ISession
from uiauto_core.waits import wait_until

from .jab_bridge import JABBridge


class JavaFXSession(ISession):
    """
    JavaFX session implementation using Java Access Bridge.
    
    Manages JavaFX application lifecycle and window access via JAB.
    """
    
    def __init__(
        self,
        jvm_path: Optional[str] = None,
        default_timeout: float = 10.0,
        polling_interval: float = 0.2,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize JavaFX session.
        
        Args:
            jvm_path: Optional path to JVM
            default_timeout: Default timeout for waits
            polling_interval: Polling interval for waits
            logger: Optional logger instance
        """
        self.default_timeout = float(default_timeout)
        self.polling_interval = float(polling_interval)
        self.log = logger or logging.getLogger("uiauto_javafx")
        
        self.bridge = JABBridge(jvm_path=jvm_path, logger=self.log)
        self.process: Optional[subprocess.Popen] = None
        self._started_pid: Optional[int] = None
        self._app_window = None
    
    def start(self, app_path: str, **kwargs) -> int:
        """
        Start a JavaFX application.
        
        Args:
            app_path: Path to Java application (jar or main class)
            **kwargs: Additional arguments
                - args: List of command line arguments
                - wait_for_idle: Wait for application to be ready
                - working_dir: Working directory for process
                
        Returns:
            Process ID
        """
        args = kwargs.get('args', [])
        wait_for_idle = kwargs.get('wait_for_idle', False)
        working_dir = kwargs.get('working_dir', None)
        
        # Build command
        if app_path.endswith('.jar'):
            cmd = ['java', '-jar', app_path] + (args if args else [])
        else:
            # Assume it's a class name
            cmd = ['java', app_path] + (args if args else [])
        
        self.log.info(f"Starting JavaFX app: {' '.join(cmd)}")
        
        self.process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._started_pid = self.process.pid
        
        # Give application time to start and become accessible
        if wait_for_idle:
            time.sleep(3.0)
        else:
            time.sleep(1.5)
        
        self.log.info(f"Started PID={self._started_pid}")
        return self._started_pid
    
    def connect(self, **kwargs) -> None:
        """
        Connect to an existing JavaFX application.
        
        Args:
            **kwargs: Connection parameters
                - pid: Process ID
                - window_title: Window title to find
        """
        pid = kwargs.get('pid')
        window_title = kwargs.get('window_title')
        
        if pid:
            self._started_pid = pid
            self.log.info(f"Connected to PID={pid}")
        
        if window_title:
            # Try to find window by title
            window = self.bridge.get_window_by_title(window_title)
            if window:
                self._app_window = window
                self.log.info(f"Found window: {window_title}")
            else:
                self.log.warning(f"Could not find window: {window_title}")
    
    def desktop_window(self, **kwargs) -> Any:
        """
        Get a window from desktop (all accessible windows).
        
        Args:
            **kwargs: Window locators
                - title: Exact window title
                - title_re: Window title regex pattern
                
        Returns:
            Window object (java.awt.Window)
        """
        title = kwargs.get('title')
        title_re = kwargs.get('title_re')
        
        if title:
            window = self.bridge.get_window_by_title(title, exact=True)
            if window:
                return window
            raise RuntimeError(f"Window not found: {title}")
        
        if title_re:
            import re
            pattern = re.compile(title_re)
            windows = self.bridge.get_all_windows()
            for w in windows:
                try:
                    w_title = str(w.getTitle()) if hasattr(w, 'getTitle') else str(w.getName())
                    if pattern.search(w_title):
                        return w
                except Exception:
                    pass
            raise RuntimeError(f"Window not found matching: {title_re}")
        
        # Return first visible window
        windows = self.bridge.get_all_windows()
        if windows:
            return windows[0]
        
        raise RuntimeError("No visible windows found")
    
    def app_window(self, **kwargs) -> Any:
        """
        Get window from connected application.
        
        Args:
            **kwargs: Window locators (same as desktop_window)
            
        Returns:
            Window object
        """
        # For JavaFX, we don't have a strict app connection like pywinauto
        # Fall back to desktop search
        return self.desktop_window(**kwargs)
    
    def close_main_windows(self, timeout: float = 5.0) -> None:
        """
        Close main windows of the application.
        
        Args:
            timeout: Timeout in seconds
        """
        if self._app_window:
            try:
                # Try to dispatch window closing event
                from java.awt.event import WindowEvent
                event = WindowEvent(self._app_window, WindowEvent.WINDOW_CLOSING)
                self._app_window.dispatchEvent(event)
                self.log.info("Dispatched WINDOW_CLOSING event")
            except Exception as e:
                self.log.warning(f"Failed to close window: {e}")
        
        # Wait for process to exit
        if self.process:
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.log.warning("Process did not exit within timeout")
    
    def kill(self) -> None:
        """Force kill the application process."""
        if self.process:
            try:
                self.process.kill()
                self.process.wait(timeout=5.0)
                self.log.info("Process killed")
            except Exception as e:
                self.log.error(f"Failed to kill process: {e}")
    
    def sleep_brief(self, seconds: float) -> None:
        """Sleep for a brief period (internal use)."""
        time.sleep(seconds)
