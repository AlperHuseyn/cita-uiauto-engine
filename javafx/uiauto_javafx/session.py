# javafx/uiauto_javafx/session.py
"""JavaFX session implementation using Java Access Bridge."""
from __future__ import annotations
import os
import subprocess
import time
import logging
from typing import Any, Dict, Optional

from uiauto_core.interfaces import ISession
from uiauto_core.waits import wait_until

from .jab_bridge import JABBridge


class JavaFXSession(ISession):
    """
    JavaFX session implementation using Java Access Bridge.
    
    Manages JavaFX application lifecycle and provides window access via JAB.
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
        
        @param jvm_path Optional path to JVM library
        @param default_timeout Default timeout for operations
        @param polling_interval Polling interval for waits
        @param logger Optional logger instance
        """
        self.default_timeout = float(default_timeout)
        self.polling_interval = float(polling_interval)
        self.log = logger or logging.getLogger("uiauto.javafx")
        
        self.bridge = JABBridge(jvm_path=jvm_path, log=self.log)
        self.process: Optional[subprocess.Popen] = None
        self.root_context: Optional[Any] = None
        self._started_pid: Optional[int] = None
    
    def start(self, app_path: str, wait_for_idle: bool = False, **kwargs) -> int:
        """
        Start a JavaFX application.
        
        @param app_path Path to application JAR or executable
        @param wait_for_idle Whether to wait for application to be idle
        @param kwargs Additional arguments (e.g., java_args, app_args)
        @return Process ID
        """
        if not os.path.exists(app_path):
            raise FileNotFoundError(f"Application not found: {app_path}")
        
        self.log.info(f"Starting JavaFX app: {app_path}")
        
        # Build command
        java_args = kwargs.get("java_args", [])
        app_args = kwargs.get("app_args", [])
        
        if app_path.endswith(".jar"):
            cmd = ["java"] + java_args + ["-jar", app_path] + app_args
        else:
            # Assume it's an executable
            cmd = [app_path] + app_args
        
        # Start process
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._started_pid = self.process.pid
        
        self.log.info(f"Started PID={self._started_pid}")
        
        # Wait for application window to appear
        if wait_for_idle:
            time.sleep(2.0)  # Give app time to initialize
        
        return self._started_pid
    
    def connect(self, **kwargs) -> None:
        """
        Connect to existing JavaFX application.
        
        @param kwargs Connection parameters (e.g., pid, title)
        
        Note: Connecting to existing Java processes via JAB is limited.
        This is a placeholder implementation.
        """
        self.log.info(f"Connecting to JavaFX app with: {kwargs}")
        
        if "pid" in kwargs:
            self._started_pid = kwargs["pid"]
        
        # In a real implementation, would need to:
        # 1. Find the Java process
        # 2. Attach to its accessibility context
        # 3. Get root context
        
        self.log.warning("connect: Limited implementation - may not work for all scenarios")
    
    def desktop_window(self, **kwargs) -> Any:
        """
        Get a window from desktop using search parameters.
        
        @param kwargs Window search parameters (title, title_re, etc.)
        @return Window context (AccessibleContext)
        
        Note: This is a simplified implementation that searches for windows
        using the JAB bridge.
        """
        title = kwargs.get("title")
        title_re = kwargs.get("title_re")
        
        if title:
            return self.bridge.find_window_by_title(title, exact=True)
        elif title_re:
            # Would need to implement regex matching
            self.log.warning("title_re not fully supported in JavaFX session")
            return self.bridge.find_window_by_title(title_re, exact=False)
        
        # Fallback: return root context if we have one
        return self.root_context
    
    def app_window(self, **kwargs) -> Any:
        """
        Get a window from started/connected application.
        
        @param kwargs Window search parameters
        @return Window context
        """
        # For JavaFX, we typically work with the root accessible context
        # which represents the main application window
        
        if self.root_context:
            return self.root_context
        
        # Try desktop_window as fallback
        return self.desktop_window(**kwargs)
    
    def close_main_windows(self, timeout: float = 5.0) -> None:
        """
        Close main windows of the application.
        
        @param timeout Timeout for close operation
        """
        if not self.process:
            return
        
        self.log.info("Closing main windows")
        
        # Try graceful termination first
        try:
            self.process.terminate()
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.log.warning("Process did not terminate gracefully, killing")
            self.process.kill()
        except Exception as e:
            self.log.error(f"Error closing windows: {e}")
    
    def kill(self) -> None:
        """Force kill the application process."""
        if self.process:
            self.log.info("Killing application process")
            try:
                self.process.kill()
                self.process.wait(timeout=5.0)
            except Exception as e:
                self.log.error(f"Error killing process: {e}")
    
    def set_root_context(self, context: Any):
        """
        Set the root accessible context for this session.
        
        @param context AccessibleContext representing application root
        
        This is typically called after starting the application or
        discovering its window through JAB.
        """
        self.root_context = context
        self.log.info("Root context set")
