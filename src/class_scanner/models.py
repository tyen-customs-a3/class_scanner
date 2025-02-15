from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any, List, TypedDict
from enum import Enum, auto
from datetime import datetime

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            'name': self.name,
            'raw_value': self.raw_value,
            'value_type': self.value_type.name if self.value_type else None,
            'is_array': self.is_array,
            'array_values': self.array_values
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PropertyValue':
        """Create instance from dictionary"""
        value_type = PropertyValueType[data['value_type']] if data['value_type'] else None
        return cls(
            name=data['name'],
            raw_value=data['raw_value'],
            value_type=value_type,
            is_array=data['is_array'],
            array_values=data['array_values']
        )

# Class definitions
@dataclass
class ClassData:
    """Core class definition data structure"""
    name: str
    parent: str
    properties: Dict[str, Any]
    source_file: Path
    container: str = ""
    config_type: str = ""
    scope: int = 0
    category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            'name': self.name,
            'parent': self.parent,
            'properties': {
                k: v.to_dict() if isinstance(v, PropertyValue) else v
                for k, v in self.properties.items()
            },
            'source_file': str(self.source_file),
            'container': self.container,
            'config_type': self.config_type,
            'scope': self.scope,
            'category': self.category
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassData':
        """Create instance from dictionary"""
        properties = {}
        for k, v in data['properties'].items():
            if isinstance(v, dict) and all(key in v for key in ['name', 'raw_value']):
                properties[k] = PropertyValue.from_dict(v)
            else:
                properties[k] = v

        return cls(
            name=data['name'],
            parent=data['parent'],
            properties=properties,
            source_file=Path(data['source_file']),
            container=data['container'],
            config_type=data['config_type'],
            scope=data['scope'],
            category=data['category']
        )

    @property
    def display_name(self) -> Optional[str]:
        """Get display name from properties if it exists"""
        if display_prop := self.properties.get('displayName'):
            return display_prop.value
        return None

class ClassDict(TypedDict):
    parent: str
    properties: Dict[str, Any]
    container: str

# Type aliases for better compatibility
SectionDict = Dict[str, ClassDict]
ConfigSections = Dict[str, SectionDict]

# Make sure the interface matches Dict[str, Dict[str, Dict[str, Any]]]
ClassSectionsDict = Dict[str, Dict[str, Dict[str, Any]]]

# PBO handling
@dataclass(frozen=True)
class PboInfo:
    path: Path
    prefix: str
    addon_name: str
    timestamp: float

@dataclass
class PboScanData:
    classes: Dict[str, ClassData]
    source: str
    last_accessed: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            'classes': {
                name: {
                    'name': c.name,
                    'parent': c.parent,
                    'properties': {
                        k: v.to_dict() if isinstance(v, PropertyValue) else v
                        for k, v in c.properties.items()
                    },
                    'source_file': str(c.source_file),
                    'container': c.container,
                    'config_type': c.config_type,
                    'scope': c.scope,
                    'category': c.category
                } for name, c in self.classes.items()
            },
            'source': self.source,
            'last_accessed': self.last_accessed.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PboScanData':
        """Create from serialized dictionary"""
        return cls(
            classes={
                name: ClassData(
                    name=c['name'],
                    parent=c['parent'],
                    properties={
                        k: PropertyValue.from_dict(v) if isinstance(v, dict) and 'raw_value' in v else v
                        for k, v in c['properties'].items()
                    },
                    source_file=Path(c['source_file']),
                    container=c['container'],
                    config_type=c['config_type'],
                    scope=c['scope'],
                    category=c['category']
                ) for name, c in data['classes'].items()
            },
            source=data['source'],
            last_accessed=datetime.fromisoformat(data['last_accessed'])
        )

@dataclass
class ClassObject:
    """Represents a parsed class object with its hierarchy"""
    name: str
    parent: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    nested_classes: List['ClassObject'] = field(default_factory=list)
    container: Optional[str] = None

    def find_nested_class(self, name: str) -> Optional['ClassObject']:
        """Find a nested class by name"""
        for cls in self.nested_classes:
            if cls.name == name:
                return cls
        return None

    def find_nested_classes_by_type(self, class_type: str) -> List['ClassObject']:
        """Find all nested classes that inherit from a specific type"""
        results = []
        if self.parent == class_type:
            results.append(self)
        for cls in self.nested_classes:
            results.extend(cls.find_nested_classes_by_type(class_type))
        return results

class CacheFileStructure(TypedDict):
    max_cache_size: int
    last_updated: str
    pbo_cache: Dict[str, Dict[str, Any]]
    class_cache: Dict[str, Dict[str, Any]]
