from typing import Dict, List, Optional, Mapping, Set
from dataclasses import dataclass, field
from types import MappingProxyType
from datetime import datetime
import logging
import threading
from pathlib import Path
import json
import time

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class CacheConfig:
    """Cache configuration settings"""
    max_size: int = 1000000000
    max_age: int = 3600  # seconds

    @property
    def cache_max_age(self) -> int:
        return self.max_age

@dataclass(frozen=True)
class ClassCache:
    """Immutable in-memory cache container"""
    hierarchies: Mapping[str, ClassHierarchy] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'hierarchies', MappingProxyType(dict(self.hierarchies)))

    @classmethod
    def create(cls, hierarchies: Dict[str, ClassHierarchy]) -> 'ClassCache':
        return cls(hierarchies=hierarchies, last_updated=datetime.now())

class ClassCacheManager:
    """Manages in-memory class hierarchy cache"""
    
    def __init__(self, config: Optional[CacheConfig] = None) -> None:
        self._config = config or CacheConfig()
        self._cache: Optional[ClassCache] = None
        self._lock = threading.RLock()  # Reentrant lock for thread safety

    def add_hierarchy(self, source: str, hierarchy: ClassHierarchy) -> None:
        """Add or update a class hierarchy in cache."""
        with self._lock:
            hierarchies = {}
            if self._cache:
                hierarchies.update(self._cache.hierarchies)
            hierarchies[source] = hierarchy

            if len(hierarchies) > self._config.max_size:
                raise ValueError(f"Cache size exceeded: {len(hierarchies)} > {self._config.max_size}")

            self._cache = ClassCache.create(hierarchies)

    def get_hierarchy(self, source: str) -> Optional[ClassHierarchy]:
        """Get cached hierarchy by source."""
        with self._lock:
            return self._cache.hierarchies.get(source) if self._cache else None

    def get_all_hierarchies(self) -> Dict[str, ClassHierarchy]:
        """Get all cached hierarchies."""
        with self._lock:
            return dict(self._cache.hierarchies) if self._cache else {}

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache = None

    def is_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache:
            return False
        return (datetime.now() - self._cache.last_updated).seconds < self._config.max_age

    def find_classes_with_parent(self, parent_name: str) -> Dict[str, Set[str]]:
        """Find all classes inheriting from given parent."""
        results = {}
        if not self._cache:
            return results

        for source, hierarchy in self._cache.hierarchies.items():
            children = {
                name for name, info in hierarchy.classes.items()
                if info.parent == parent_name
            }
            if children:
                results[source] = children
        return results

    def find_classes_with_property(self, property_name: str) -> Dict[str, Set[str]]:
        """Find all classes with given property."""
        results = {}
        if not self._cache:
            return results

        for source, hierarchy in self._cache.hierarchies.items():
            classes = hierarchy.find_classes_with_property(property_name)
            if classes:
                results[source] = classes
        return results

    def find_similar_classes(self, class_name: str, threshold: float = 0.75) -> List[str]:
        """Find similar class names using Levenshtein distance"""
        if not self._cache:
            return []
            
        results = []
        for hierarchy in self._cache.hierarchies.values():
            for name in hierarchy.classes:
                distance = self._levenshtein_distance(class_name.lower(), name.lower())
                if distance <= (1 - threshold) * len(class_name):
                    results.append(name)
        return sorted(results)

    def validate_class(self, class_name: str, inheritance_chain: Optional[List[str]] = None) -> bool:
        """Validate class exists with correct inheritance"""
        if not self._cache:
            return False
            
        for hierarchy in self._cache.hierarchies.values():
            if class_name in hierarchy.classes:
                if not inheritance_chain:
                    return True
                    
                actual_chain = hierarchy.get_inheritance_chain(class_name)
                return actual_chain == inheritance_chain
                
        return False

from pathlib import Path
from typing import Dict, Optional
import time
from .models.simple_models import PboClasses

class SimpleCache:
    """Simple cache for PBO class data"""
    
    def __init__(self, max_age: int = 3600):
        self._cache: Dict[str, PboClasses] = {}
        self._timestamps: Dict[str, float] = {}
        self.max_age = max_age
        
    def get(self, pbo_path: Path) -> Optional[PboClasses]:
        """
        Get cached classes if not expired
        
        Args:
            pbo_path: Path to PBO file
            
        Returns:
            Cached PboClasses if valid, None if expired or not found
        """
        key = str(pbo_path)
        if key in self._cache:
            if time.time() - self._timestamps[key] < self.max_age:
                return self._cache[key]
            self._remove(key)
        return None
        
    def set(self, pbo_path: Path, classes: PboClasses) -> None:
        """
        Cache PBO class data with timestamp
        
        Args:
            pbo_path: Path to PBO file
            classes: PboClasses data to cache
        """
        key = str(pbo_path)
        self._cache[key] = classes
        self._timestamps[key] = time.time()
        
    def _remove(self, key: str) -> None:
        """Remove item from cache"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        
    def clear(self) -> None:
        """Clear all cached data"""
        self._cache.clear()
        self._timestamps.clear()
