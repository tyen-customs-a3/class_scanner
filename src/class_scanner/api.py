from pathlib import Path
from typing import Dict, Callable, Optional, Any, Union
import logging
from .cache import ClassCache
from .scanner import Scanner
from .models import PboScanData

logger = logging.getLogger(__name__)

class ClassAPI:
    """Main API class for class scanning functionality"""
    
    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self.scanner = Scanner()
        self.cache = ClassCache()
        self.cache_dir = cache_dir
        self._progress_callback: Optional[Callable[[str], None]] = None
        
        if cache_dir and cache_dir.exists():
            try:
                cache_file = cache_dir / 'pbo_cache.json'
                if cache_file.exists():
                    self.cache = ClassCache.load_from_disk(cache_file)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")

    def set_progress_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for progress updates"""
        self._progress_callback = callback

    def clear_cache(self) -> None:
        """Clear the cache"""
        self.cache.clear()

    def scan_directory(self, directory: Union[str, Path], file_limit: Optional[int] = None) -> Dict[str, PboScanData]:
        """Scan a directory for PBO files and their classes"""
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            return {}

        results: Dict[str, PboScanData] = {}
        pbo_files = list(directory.rglob('*.pbo'))[:file_limit] if file_limit else list(directory.rglob('*.pbo'))

        for pbo_file in pbo_files:
            if self._progress_callback:
                self._progress_callback(f"Processing {pbo_file}")

            if result := self.scan_pbo(pbo_file):
                results[str(pbo_file)] = result
                
        # Save cache if directory specified
        if self.cache_dir:
            cache_file = self.cache_dir / 'pbo_cache.json'
            try:
                self.cache.save_to_disk(cache_file)
            except Exception as e:
                logger.error(f"Failed to save cache: {e}")

        return results

    def scan_pbo(self, pbo_path: Union[str, Path]) -> Optional[PboScanData]:
        """Scan a single PBO file for class definitions"""
        pbo_path = Path(pbo_path)
        if not pbo_path.exists():
            logger.debug("Invalid file path: %s", pbo_path)
            return None

        # Check cache first
        if cached := self.cache.get(pbo_path):
            return cached

        # Scan if not in cache
        if result := self.scanner.scan_pbo(pbo_path):
            self.cache.add(pbo_path, result)
            return result

        return None
