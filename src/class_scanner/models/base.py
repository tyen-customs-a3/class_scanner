from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Set, Optional, Dict, List, Type, Any, Union, TypeVar

def parse_property_value(raw_value: str) -> str:
    """Parse a property value, handling arrays and quotes"""
    value = raw_value.strip()
    if value.startswith('{') and value.endswith('}'):
        items = [v.strip(' "\'') for v in value[1:-1].split(',')]
        return ','.join(v for v in items if v)
    return value.strip(' "\'')

@dataclass(frozen=True)
class CodeReference:
    """Represents a code reference result"""
    file_path: Path
    line_number: int
    line_content: str
    source: str

@dataclass(frozen=True)
class ClassDefinition:
    """Represents a class definition found in code"""
    name: str
    parent: Optional[str]
    properties: Dict[str, str]
    file_path: Path
    source: str

@dataclass(frozen=True)
class ClassInfo:
    """Represents a class with its properties and inheritance info"""
    name: str
    parent: Optional[str]
    properties: Dict[str, str]
    file_path: Path
    source: str
    children: Set[str] = field(default_factory=frozenset)
    inherited_properties: Dict[str, str] = field(default_factory=dict)
    type: str = 'class'  # 'class' or 'enum'

    def __post_init__(self):
        """Convert mutable collections to immutable"""
        if not isinstance(self.children, frozenset):
            object.__setattr__(self, 'children', frozenset(self.children))
        if isinstance(self.properties, dict):
            object.__setattr__(self, 'properties', MappingProxyType(dict(self.properties)))
        if isinstance(self.inherited_properties, dict):
            object.__setattr__(self, 'inherited_properties', MappingProxyType(dict(self.inherited_properties)))

    def get_all_properties(self) -> Dict[str, str]:
        """Get all properties including inherited ones"""
        return {**self.inherited_properties, **self.properties}

    def has_property(self, name: str) -> bool:
        """Check if property exists (including inherited)"""
        return name in self.properties or name in self.inherited_properties

    def get_inheritance_chain(self) -> List[str]:
        """Get inheritance chain from root to this class"""
        chain = [self.name]
        current = self.parent
        visited = {self.name}
        
        while current and current not in visited:
            chain.append(current)
            visited.add(current)
            if hasattr(self, 'inherited_properties'):
                # Try to get next parent from inherited properties
                current = self.inherited_properties.get('parent')
            else:
                break
                
        return list(reversed(chain))

    def validate_required_properties(self, required: Set[str]) -> List[str]:
        """Validate that required properties exist"""
        missing = []
        for prop in required:
            if not self.has_property(prop):
                missing.append(f"Missing required property: {prop}")
        return missing

    def validate_property_types(self, type_map: Dict[str, Type[Any]]) -> List[str]:
        """Validate property types"""
        errors = []
        for prop_name, expected_type in type_map.items():
            if self.has_property(prop_name):
                value = self.properties.get(prop_name) or self.inherited_properties.get(prop_name)
                try:
                    expected_type(value)
                except (ValueError, TypeError):
                    errors.append(f"Invalid type for {prop_name}: expected {expected_type.__name__}")
        return errors

@dataclass(frozen=True)
class RawClassDef:
    """Raw class definition before hierarchy processing"""
    name: str
    parent: Optional[str]
    properties: Dict[str, str]
    file_path: Path
    source: str
    type: str = 'class'

    def to_class_info(self) -> ClassInfo:
        """Convert to ClassInfo"""
        return ClassInfo(
            name=self.name,
            parent=self.parent,
            properties=self.properties,
            file_path=self.file_path,
            source=self.source,
            type=self.type
        )

@dataclass(frozen=True)
class ClassHierarchy:
    """Represents the entire class hierarchy for a mod"""
    classes: Dict[str, ClassInfo]
    root_classes: Set[str]
    source: str
    invalid_classes: Set[str] = field(default_factory=set)
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def hierarchies(self) -> Dict[str, 'ClassHierarchy']:
        """Get all hierarchies including this one, keyed by source"""
        return {self.source: self}

    @property
    def success(self) -> bool:
        """Check if the hierarchy was successfully built without errors"""
        return bool(self.classes) and not self.invalid_classes

    def get_all_children(self, class_name: str, include_indirect: bool = True) -> Set[str]:
        """Get all descendant classes recursively"""
        if class_name not in self.classes:
            return set()
        
        if not include_indirect:
            return self.classes[class_name].children
            
        result = set()
        to_process = {class_name}
        
        while to_process:
            current = to_process.pop()
            if current in self.classes:
                children = self.classes[current].children
                result.update(children)
                to_process.update(children)
                
        return result

    def get_inheritance_chain(self, class_name: str, bottom_up: bool = False) -> List[str]:
        """Get inheritance chain for a class"""
        if class_name not in self.classes:
            return []
            
        chain = [class_name]
        current = self.classes[class_name]
        
        while current.parent:
            if current.parent in self.classes:
                chain.append(current.parent)
                current = self.classes[current.parent]
            else:
                break
                
        return chain if bottom_up else list(reversed(chain))

    def find_classes_with_property(self, property_name: str) -> Set[str]:
        """Find all classes that have a specific property"""
        return {
            name for name, info in self.classes.items()
            if info.has_property(property_name)
        }

@dataclass(frozen=True)
class UnprocessedClasses:
    """Container for unprocessed class definitions"""
    classes: Dict[str, RawClassDef]
    source: str
    last_updated: datetime = field(default_factory=datetime.now)

    def build_hierarchy(self) -> ClassHierarchy:
        """Process raw classes into a complete hierarchy"""
        processed = {}
        invalid = set()
        roots = set()
        
        # First pass: detect cycles and invalid inheritance
        for name, raw in self.classes.items():
            chain = []
            current = name
            visited = set()
            
            while current and current not in visited:
                chain.append(current)
                visited.add(current)
                current = self.classes[current].parent if current in self.classes else None
                
                if current in chain:
                    invalid.update(chain[chain.index(current):])
                    break
        
        # Second pass: build valid hierarchies
        for name, raw in self.classes.items():
            if name in invalid:
                continue
                
            # Convert raw definition to ClassInfo
            info = raw.to_class_info()
            
            # Add children information
            children = {
                c for c, r in self.classes.items()
                if r.parent == name and c not in invalid
            }
            
            # Get inherited properties
            inherited = self._get_inherited_properties(name)
            
            processed[name] = ClassInfo(
                name=name,
                parent=raw.parent,
                properties=raw.properties,
                file_path=raw.file_path,
                source=raw.source,
                children=children,
                inherited_properties=inherited,
                type=raw.type
            )
            
            if not raw.parent:
                roots.add(name)
        
        return ClassHierarchy(
            classes=processed,
            root_classes=roots,
            source=self.source,
            invalid_classes=invalid
        )

    def _get_inherited_properties(self, class_name: str) -> Dict[str, str]:
        """Get inherited properties for a class"""
        result = {}
        current = self.classes.get(class_name)
        visited = {class_name}
        
        while current and current.parent:
            if current.parent in visited:
                break
                
            parent = self.classes.get(current.parent)
            if parent:
                result.update(parent.properties)
                visited.add(current.parent)
                current = parent
            else:
                break
                
        return result
