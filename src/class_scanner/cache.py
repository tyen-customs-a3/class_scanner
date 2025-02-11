import logging
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
import json

from .models import PboScanData

class ClassCache:
    """Simple in-memory cache for PBO scanning results"""
    
    def __init__(self, max_cache_size: int = 100_000_000):
        self._cache: Dict[str, PboScanData] = {}
        self.max_cache_size = max_cache_size
        self._last_updated = datetime.now()
        self._max_age = timedelta(hours=1)
        self._logger = logging.getLogger(__name__)

    def add(self, path: str | Path, pbo_data: PboScanData) -> None:
        """Add or update PboClasses in cache"""
        if len(self._cache) >= self.max_cache_size:
            # Remove oldest entries if cache is full
            sorted_items = sorted(self._cache.items(), 
                                key=lambda x: x[1].last_accessed)
            while len(self._cache) >= self.max_cache_size:
                oldest = sorted_items.pop(0)
                del self._cache[oldest[0]]
            
        normalized_path = str(path).replace('\\', '/')
        self._cache[normalized_path] = pbo_data
        self._last_updated = datetime.now()
        self._logger.debug(f"Cache updated for {normalized_path}")

    def get(self, path: str | Path) -> Optional[PboScanData]:
        """Get PboScanData by path"""
        path_str = str(path).replace('\\', '/')
        if result := self._cache.get(path_str):
            return result
        return None

    def is_valid(self) -> bool:
        """Check if cache is still valid"""
        return datetime.now() - self._last_updated < self._max_age

    def clear(self) -> None:
        """Clear the cache"""
        self._cache.clear()
        self._last_updated = datetime.now()

    def save_to_disk(self, cache_file: Path) -> None:
        """Save cache to disk"""
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_data = {
            'max_cache_size': self.max_cache_size,
            'last_updated': self._last_updated.isoformat(),
            'cache': {
                path: pbo.to_dict() 
                for path, pbo in self._cache.items()
            }
        }
        
        with cache_file.open('w') as f:
            json.dump(cache_data, f, indent=2)
        
        self._logger.info(f"Cache saved to {cache_file}")

    @classmethod
    def load_from_disk(cls, cache_file: Path) -> 'ClassCache':
        """Load cache from disk"""
        logger = logging.getLogger(__name__)
        
        try:
            with cache_file.open('r') as f:
                data = json.load(f)
                
            cache = cls(max_cache_size=data['max_cache_size'])
            cache._last_updated = datetime.fromisoformat(data['last_updated'])
            cache._cache = {
                path: PboScanData.from_dict(pbo_data)
                for path, pbo_data in data['cache'].items()
            }
            
            logger.debug(f"Successfully loaded cache with {len(cache._cache)} entries")
            return cache
            
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            raise
