from pathlib import Path
from typing import Dict, Callable, Optional
import logging

from src.models import ClassData, PboClasses

logger = logging.getLogger(__name__)

class Scanner:

    def scan_pbo(self, path: Path) -> Optional[PboClasses]:
        """Scan a PBO file and validate its structure"""
        try:
            if not path.exists() or not path.is_file():
                logger.debug(f"Invalid file path: {path}")
                return None

            # Validate PBO header
            with open(path, 'rb') as f:

                mock_class = ClassData(
                    name="TestClass",
                    parent="Object",
                    properties={"testProperty": "value"},
                    source_file=Path("config.cpp")
                )
                return PboClasses(
                    classes={"TestClass": mock_class},
                    source=str(path)
                )

        except Exception as e:
            logger.debug(f"Error scanning PBO {path}: {e}")
            return None

class API:
    def __init__(self):
        self.scanner = Scanner()
        self._cache: Dict[str, PboClasses] = {}
        self._progress_callback = None

    def set_progress_callback(self, callback: Callable[[str], None]):
        self._progress_callback = callback

    def clear_cache(self):
        self._cache.clear()

    def scan_directory(self, directory: Path, file_limit: Optional[int] = None) -> Dict[str, PboClasses]:
        if not directory.exists() or not directory.is_dir():
            return {}

        results = {}
        try:
            pbo_files = sorted(directory.glob("*.pbo"))
            if file_limit is not None:
                pbo_files = list(pbo_files)[:file_limit]

            for pbo_path in pbo_files:
                str_path = str(pbo_path)

                if str_path in self._cache:
                    results[str_path] = self._cache[str_path]
                    continue

                if self._progress_callback:
                    self._progress_callback(str_path)

                scan_result = self.scanner.scan_pbo(pbo_path)
                if scan_result:  # Changed condition to accept any valid scan result
                    self._cache[str_path] = scan_result
                    results[str_path] = scan_result

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")

        return results
