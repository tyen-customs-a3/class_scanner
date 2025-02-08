from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

@dataclass(frozen=True)
class ClassInfo:
    """Core class definition model"""
    name: str
    parent: Optional[str]
    properties: Dict[str, str]
    file_path: Path
    source: str
    inherited_properties: Dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class PboInfo:
    """Metadata about a PBO file"""
    path: Path
    prefix: str
    addon_name: str
    timestamp: float
    
@dataclass(frozen=True)
class ClassDefinition:
    """Raw class definition from config files"""
    name: str
    parent: Optional[str]
    properties: Dict[str, str]
    source_file: Path
    pbo_info: PboInfo


@dataclass(frozen=True)
class CacheConfig:
    """Cache configuration settings"""
    max_size: int = 1000
    max_age: int = 3600  # seconds

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

class ClassData:
    def __init__(self, name: str, parent: str, properties: Dict, source_file: Path):
        self.name = name
        self.parent = parent
        self.properties = properties
        self.source_file = source_file

class PboClasses:
    def __init__(self, classes: Dict[str, ClassData], source: str):
        self.classes = classes
        self.source = source