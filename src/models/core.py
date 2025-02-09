from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any


@dataclass(frozen=True)
class CacheConfig:
    """Cache configuration settings"""
    max_size: int = 1000
    max_age: int = 3600


@dataclass(frozen=True)
class ScannerConfig:
    """Configuration for scanning operations"""
    max_file_size: int = 100_000_000
    parse_timeout: int = 30
    extensions: frozenset[str] = frozenset({'.cpp', '.hpp', '.h', '.sqf', '.bin'})


@dataclass(frozen=True)
class StorageConfig:
    """Configuration for storage operations"""
    db_path: Optional[Path] = None
    cache_config: Optional[CacheConfig] = None
    max_cache_size: int = 1000


@dataclass(frozen=True)
class PboInfo:
    """Metadata about a PBO file"""
    path: Path
    prefix: str
    addon_name: str
    timestamp: float


@dataclass
class ClassData:
    name: str
    parent: str
    properties: Dict
    source_file: Path


@dataclass
class PropertyData:
    value: Any
    raw: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert PropertyData to a dictionary for JSON serialization"""
        return {
            "value": str(self.value),  # Convert value to string to ensure JSON compatibility
            "raw": self.raw
        }


class PboClasses:
    def __init__(self, classes: Dict[str, ClassData], source: str):
        self.classes = classes
        self.source = source
