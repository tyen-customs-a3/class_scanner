import logging
from typing import Dict, Optional, Union, overload, Iterable, TypeVar, Tuple, cast
from pathlib import Path
from datetime import datetime, timedelta
import json

from .models import PboScanData, ClassData, CacheFileStructure

T = TypeVar('T', PboScanData, ClassData)

class ClassCache:
    """Cache for both PBO scan results and individual class definitions"""
    
    def __init__(self, max_cache_size: int = 100_000_000):
        self._pbo_cache: Dict[str, PboScanData] = {}
        self._class_cache: Dict[str, ClassData] = {}
        self.max_cache_size = max_cache_size
        self._last_updated = datetime.now()
        self._max_age = timedelta(hours=1)
        self._logger = logging.getLogger(__name__)

    def _normalize_path(self, path: Union[str, Path]) -> str:
        """Normalize path string for consistent caching."""
        return str(path).replace('\\', '/')

    @overload
    def add(self, path: str, data: PboScanData) -> None: ...
    
    @overload
    def add(self, path: str, data: ClassData) -> None: ...
    
    def add(self, path: str, data: Union[PboScanData, ClassData]) -> None:
        """Add item to appropriate cache based on type."""
        normalized_path = self._normalize_path(path)
        
        if isinstance(data, PboScanData):
            self._pbo_cache[normalized_path] = data
        elif isinstance(data, ClassData):
            self._class_cache[normalized_path] = data
        else:
            raise TypeError(f"Unexpected data type: {type(data)}")
            
        self._last_updated = datetime.now()

    def add_classes(self, classes: Union[Dict[str, ClassData], Iterable[Tuple[str, ClassData]]]) -> None:
        """Add multiple classes to cache at once."""
        try:
            if isinstance(classes, dict):
                for name, class_data in classes.items():
                    self.add(str(name), cast(ClassData, class_data))
            else:
                for item in classes:
                    if not isinstance(item, tuple) or len(item) != 2:
                        raise TypeError(f"Expected (str, ClassData) tuple, got {type(item)}")
                    name, class_data = item
                    if not isinstance(name, str):
                        raise TypeError(f"Class name must be str, got {type(name)}")
                    if not isinstance(class_data, ClassData):
                        raise TypeError(f"Class data must be ClassData, got {type(class_data)}")
                    self.add(name, class_data)
        except Exception as e:
            self._logger.error(f"Failed to batch add classes: {e}")

    def get(self, path: Union[str, Path]) -> Optional[PboScanData]:
        """Get PboScanData by path"""
        path_str = self._normalize_path(path)
        return self._pbo_cache.get(path_str)

    def get_class(self, name: str) -> Optional[ClassData]:
        """Get ClassData by name"""
        return self._class_cache.get(name)

    def get_all(self) -> Dict[str, ClassData]:
        all_classes = dict(self._class_cache)
        for pbo_data in self._pbo_cache.values():
            if pbo_data.classes:
                all_classes.update(pbo_data.classes)
        return all_classes

    def get_all_classes(self) -> Dict[str, ClassData]:
        """Get all cached classes combined."""
        all_classes: Dict[str, ClassData] = {}
        for pbo_data in self._pbo_cache.values():
            all_classes.update(pbo_data.classes)
        return all_classes

    def is_valid(self) -> bool:
        """Check if cache is still valid"""
        return True

    def clear(self) -> None:
        """Clear both caches"""
        self._pbo_cache.clear()
        self._class_cache.clear()
        self._last_updated = datetime.now()

    def save_to_disk(self, cache_file: Path) -> None:
        """Save both caches to disk"""
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_data: CacheFileStructure = {
            'max_cache_size': self.max_cache_size,
            'last_updated': self._last_updated.isoformat(),
            'pbo_cache': {
                path: pbo.to_dict() 
                for path, pbo in self._pbo_cache.items()
            },
            'class_cache': {
                name: cls.to_dict()
                for name, cls in self._class_cache.items()
            }
        }
        
        with cache_file.open('w') as f:
            json.dump(cache_data, f, indent=2)
        
        self._logger.info(f"Cache saved to {cache_file}")

    @classmethod
    def load_from_disk(cls, cache_file: Path) -> 'ClassCache':
        """Load both caches from disk"""
        logger = logging.getLogger(__name__)
        
        try:
            with cache_file.open('r') as f:
                data = json.load(f)
                
            cache = cls(max_cache_size=data['max_cache_size'])
            cache._last_updated = datetime.fromisoformat(data['last_updated'])
            
            cache._pbo_cache = {
                path: PboScanData.from_dict(pbo_data)
                for path, pbo_data in data.get('pbo_cache', {}).items()
            }
            
            cache._class_cache = {
                name: ClassData.from_dict(cls_data) if isinstance(cls_data, dict) else cls_data
                for name, cls_data in data.get('class_cache', {}).items()
            }
            
            logger.debug(f"Loaded cache with {len(cache._pbo_cache)} PBOs and {len(cache._class_cache)} classes")
            return cache
            
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            raise
