"""
ORCA Agent Core Package.
"""
import sys
from pathlib import Path

# Ensure backend/ai-services is in sys.path whenever app is imported
_pkg_root = str(Path(__file__).resolve().parent.parent)
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

__version__ = "1.0.0"
