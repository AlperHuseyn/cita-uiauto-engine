# main_ui.py
"""
Entry point for cita-uiauto-engine Desktop UI.
"""

import sys
import os

# Ensure uiauto package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uiauto_ui.app import main

if __name__ == "__main__":
    main()