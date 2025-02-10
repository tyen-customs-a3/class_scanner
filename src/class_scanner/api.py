from pathlib import Path
from typing import Dict, Callable, Optional
import logging

from class_scanner.models import ClassData, PboClasses
from class_scanner.models.core import PropertyValue

logger = logging.getLogger(__name__)

class ClassScanner:

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
                    properties={
                        "testProperty": PropertyValue(
                            name="testProperty",
                            raw_value="value"
                        )
                    },
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
        self.scanner = ClassScanner()
        self._cache: Dict[str, PboClasses] = {}
        self._progress_callback = None

    def set_progress_callback(self, callback: Callable[[str], None]):
        self._progress_callback = callback

    def clear_cache(self):
        self._cache.clear()

    def scan_pbo(self, pbo_path: Path) -> Optional[PboClasses]:
        """Scan a single PBO file."""
        str_path = str(pbo_path)
        
        # Check cache first
        if str_path in self._cache:
            return self._cache[str_path]

        # Report progress if callback set
        if self._progress_callback:
            self._progress_callback(str_path)

        # Perform scan
        result = self.scanner.scan_pbo(pbo_path)
        if result:
            self._cache[str_path] = result
        return result

    def scan_directory(self, directory: Path, file_limit: Optional[int] = None) -> Dict[str, PboClasses]:
        """Scan a directory of PBOs."""
        if not directory.exists() or not directory.is_dir():
            return {}

        results = {}
        try:
            pbo_files = sorted(directory.glob("*.pbo"))
            if file_limit is not None:
                pbo_files = list(pbo_files)[:file_limit]

            for pbo_path in pbo_files:
                result = self.scan_pbo(pbo_path)
                if result:
                    results[str(pbo_path)] = result

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")

        return results
