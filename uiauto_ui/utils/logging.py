# uiauto_ui/utils/logging.py
"""
Structured logging configuration for the UI application.
Provides both console and file logging with proper formatting.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .paths import get_log_file_path

# Module-level logger cache
_loggers: dict = {}
_initialized: bool = False


class UILogFormatter(logging.Formatter):
    """Custom formatter with thread and timestamp info."""
    
    def __init__(self, include_thread: bool = True):
        self.include_thread = include_thread
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = record.levelname.ljust(8)
        name = record.name
        
        if self.include_thread:
            thread = record.threadName[:12].ljust(12)
            prefix = f"[{timestamp}] [{level}] [{thread}] {name}: "
        else:
            prefix = f"[{timestamp}] [{level}] {name}: "
        
        message = record.getMessage()
        
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return prefix + message


def setup_logging(
    console_level: int = logging.DEBUG,
    file_level: int = logging.DEBUG,
    log_file: Optional[Path] = None
) -> None:
    """
    Initialize application logging.
    
    Args:
        console_level: Logging level for console output
        file_level: Logging level for file output
        log_file: Path to log file (uses default if None)
    """
    global _initialized
    
    if _initialized:
        return
    
    # Get or create log file path
    if log_file is None:
        log_file = get_log_file_path()
    
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger("uiauto_ui")
    root_logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(UILogFormatter(include_thread=False))
    root_logger.addHandler(console_handler)
    
    # File handler with rotation-friendly naming
    try:
        file_handler = logging.FileHandler(
            log_file,
            mode="a",
            encoding="utf-8"
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(UILogFormatter(include_thread=True))
        root_logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        root_logger.warning(f"Could not create log file: {e}")
    
    _initialized = True
    root_logger.info(f"Logging initialized. Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    if name not in _loggers:
        if name.startswith("uiauto_ui"):
            _loggers[name] = logging.getLogger(name)
        else:
            _loggers[name] = logging.getLogger(f"uiauto_ui.{name}")
    
    return _loggers[name]


def log_command_start(logger: logging.Logger, command: str, argv: list) -> None:
    """Log command execution start."""
    logger.info(f"Command started: {command}")
    logger.debug(f"Full argv: {argv}")


def log_command_finish(
    logger: logging.Logger,
    command: str,
    return_code: int,
    duration: float
) -> None:
    """Log command execution completion."""
    status = "SUCCESS" if return_code == 0 else f"FAILED (code={return_code})"
    logger.info(f"Command finished: {command} → {status} in {duration:.2f}s")


def log_exception(logger: logging.Logger, context: str, exception: Exception) -> None:
    """Log an exception with context."""
    logger.exception(f"Exception in {context}: {type(exception).__name__}: {exception}")