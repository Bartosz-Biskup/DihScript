"""Internal testing tool for the script-fixer app.

Imports the main app's packages from ../src so the tool can be launched
from anywhere without touching PYTHONPATH.
"""

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
