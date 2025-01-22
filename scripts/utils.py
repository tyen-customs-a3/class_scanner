import os
from pathlib import Path
from typing import Set, Dict, Any

def ensure_temp_dir(project_root: Path) -> Path:
    """Create and return temp directory in project root"""
    temp_dir = project_root / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def setup_python_path(file_path: Path) -> None:
    """Add the src directory to Python path"""
    import sys
    src_path = str(file_path.parent.parent / 'src')
    if (src_path not in sys.path):
        sys.path.insert(0, src_path)
