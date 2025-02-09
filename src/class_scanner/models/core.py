from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any, List, TypedDict
from enum import Enum, auto

# Basic configs
@dataclass(frozen=True)
class CacheConfig:
    max_size: int = 1000
    max_age: int = 3600

@dataclass(frozen=True)
class ScannerConfig:
    max_file_size: int = 100_000_000
    parse_timeout: int = 30
    extensions: frozenset[str] = frozenset({'.cpp', '.hpp', '.h', '.sqf', '.bin'})
    cache_enabled: bool = True
    cache_dir: Optional[Path] = None
    debug: bool = False

# Property value handling
class PropertyValueType(Enum):
    ARRAY = auto()
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    IDENTIFIER = auto()

@dataclass
class PropertyValue:
    name: str = ""
    raw_value: str = ""
    value_type: Optional[PropertyValueType] = None
    is_array: bool = False
    array_values: List[str] = field(default_factory=list)

    def __init__(
        self, 
        name: str = "", 
        raw_value: str = "", 
        value_type: Optional[PropertyValueType] = None,
        is_array: bool = False,
        array_values: Optional[List[str]] = None
    ) -> None:
        self.name = name
        self.raw_value = raw_value
        self.value_type = value_type
        self.is_array = is_array
        self.array_values = array_values or []

    @property
    def value(self) -> str:
        """Return the raw value for direct property access"""
        return self.raw_value

    def __eq__(self, other: Any) -> bool:
        """Allow direct comparison with strings"""
        if isinstance(other, str):
            return self.raw_value == other
        return super().__eq__(other)

# Class definitions
@dataclass
class ClassData:
    """Core class definition data structure"""
    name: str
    parent: str
    properties: Dict[str, PropertyValue]  # Must be PropertyValue, not Any
    source_file: Path
    container: str = ""
    config_type: str = ""
    scope: int = 0
    category: Optional[str] = None  # Add back category field

    @property
    def display_name(self) -> Optional[str]:
        """Get display name from properties if it exists"""
        if display_prop := self.properties.get('displayName'):
            return display_prop.value
        return None

class ClassDict(TypedDict):
    parent: str
    properties: Dict[str, PropertyValue]
    container: str

class ConfigSections(TypedDict):
    CfgPatches: Dict[str, ClassDict]
    CfgWeapons: Dict[str, ClassDict]
    CfgVehicles: Dict[str, ClassDict]
    _global: Dict[str, ClassDict]

# PBO handling
@dataclass(frozen=True)
class PboInfo:
    path: Path
    prefix: str
    addon_name: str
    timestamp: float

@dataclass
class PboClasses:
    classes: Dict[str, ClassData]
    source: str
