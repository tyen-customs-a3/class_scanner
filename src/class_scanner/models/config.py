from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set, Dict, Any

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
    extensions: Set[str] = frozenset({'.cpp', '.hpp', '.h', '.sqf', '.bin'})

@dataclass(frozen=True)
class StorageConfig:
    """Configuration for storage operations"""
    db_path: Optional[Path] = None
    cache_config: Optional[CacheConfig] = None
    max_cache_size: int = 1000
