from pathlib import Path
import logging
from typing import Callable, Dict, Optional, Union
from .cache import ClassCache
from .scanner import Scanner
from .models import PboScanData

logger = logging.getLogger(__name__)

def _normalize_path(path: Union[str, Path]) -> str:
    """Convert path to normalized string format."""
    return str(Path(path).absolute())

class ClassAPI:
    """Main API class for class scanning functionality"""
    
    def __init__(self, cache_dir: Optional[Path] = None, cache_file: Optional[Path] = None) -> None:
        self.scanner = Scanner()
        self.cache = ClassCache()
        self.cache_dir = cache_dir
        self.cache_file = cache_file
        self._progress_callback: Optional[Callable[[str], None]] = None
        
        # Try loading cache from specific file first, then fall back to directory
        if cache_file and cache_file.exists():
            try:
                self.cache = ClassCache.load_from_disk(cache_file)
            except Exception as e:
                logger.warning(f"Failed to load cache from file {cache_file}: {e}")
        elif cache_dir and cache_dir.exists():
            try:
                default_cache = cache_dir / 'pbo_cache.json'
                if default_cache.exists():
                    self.cache = ClassCache.load_from_disk(default_cache)
            except Exception as e:
                logger.warning(f"Failed to load cache from directory: {e}")

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

            if result := self.scan(pbo_file):
                results[_normalize_path(pbo_file)] = result
                
        # Save cache if directory specified
        self.save_cache()

        return results

    def scan(self, pbo_path: Union[str, Path]) -> Optional[PboScanData]:
        """Scan a single PBO file for class definitions"""
        pbo_path = Path(pbo_path)
        if not pbo_path.exists():
            logger.debug("Invalid file path: %s", pbo_path)
            return None

        normalized_path = _normalize_path(pbo_path)

        # Check cache first
        if cached := self.cache.get(normalized_path):
            return cached

        # Scan if not in cache
        if result := self.scanner.scan_pbo(pbo_path):
            self.cache.add(normalized_path, result)
            return result

        return None

    def save_cache(self) -> None:
        """Save cache to configured location."""
        if self.cache_file:
            try:
                self.cache.save_to_disk(self.cache_file)
            except Exception as e:
                logger.error(f"Failed to save cache to {self.cache_file}: {e}")
        elif self.cache_dir:
            try:
                cache_file = self.cache_dir / 'pbo_cache.json'
                self.cache.save_to_disk(cache_file)
            except Exception as e:
                logger.error(f"Failed to save cache to directory: {e}")
