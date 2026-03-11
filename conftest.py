# conftest.py – root pytest configuration for cita-uiauto-engine
#
# Ensures that both the ``uiauto`` and ``uiauto_ui`` packages are importable
# when pytest discovers and runs tests (including auto-generated scenario tests).
import sys
import os

# Insert the project root at the front of sys.path so that local package
# imports work regardless of the working directory pytest is invoked from.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
