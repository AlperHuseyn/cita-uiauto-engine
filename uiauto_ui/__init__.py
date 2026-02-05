# uiauto_ui/__init__.py
"""
cita-uiauto-engine Desktop UI

A professional PySide6-based GUI for the cita-uiauto-engine CLI tool.
Provides forms for run, inspect, and record commands with live output display.

Usage:
    python -m uiauto_ui
    
Or programmatically:
    from uiauto_ui import main
    main()
"""

__version__ = "1.2.0"
__author__ = "cita"

from .app import main

__all__ = ["main", "__version__"]