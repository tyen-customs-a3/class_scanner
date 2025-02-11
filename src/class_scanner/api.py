from pathlib import Path
from typing import Dict, Callable, Optional, Any
import logging
import struct
import io
import logging
from pathlib import Path
from typing import Dict, Optional, Callable, Union
from class_scanner.models import PboClasses
from class_scanner.scanner import Scanner

logger = logging.getLogger(__name__)

class ClassAPI:
    """Main API class for class scanning functionality"""
    
    def __init__(self) -> None:
        """Initialize API with default configuration"""
        self.scanner = Scanner()
        self._cache: Dict[str, PboClasses] = {}
        self._progress_callback: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for progress updates"""
        self._progress_callback = callback

    def clear_cache(self) -> None:
        """Clear the results cache"""
        self._cache.clear()

    def scan_directory(self, directory: Union[str, Path], file_limit: Optional[int] = None) -> Dict[str, PboClasses]:
        """Scan a directory for PBO files and their classes"""
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            return {}

        results: Dict[str, PboClasses] = {}
        processed = 0

        pbo_files = list(directory.rglob('*.pbo'))
        if file_limit:
            pbo_files = pbo_files[:file_limit]

        for pbo_file in pbo_files:
            if self._progress_callback:
                self._progress_callback(f"Processing {pbo_file}")

            if result := self.scan_pbo(pbo_file):
                results[str(pbo_file)] = result
                processed += 1

        return results

    def scan_pbo(self, pbo_path: Union[str, Path]) -> Optional[PboClasses]:
        """Scan a single PBO file for class definitions"""
        pbo_path = Path(pbo_path)
        if not pbo_path.exists():
            logger.debug("Invalid file path: %s", pbo_path)
            return None

        cache_key = str(pbo_path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if result := self.scanner.scan_pbo(pbo_path):
            self._cache[cache_key] = result
            return result

        return None
