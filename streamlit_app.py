"""
AutoTube AI - Streamlit Cloud Root Entrypoint
Ensures sys.path is correctly configured and launches the main dashboard.
"""

import sys
import runpy
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Launch main dashboard
dashboard_path = ROOT_DIR / "app" / "dashboard.py"
runpy.run_path(str(dashboard_path), run_name="__main__")
