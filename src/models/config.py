from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from pathlib import Path

@dataclass(frozen=True)
class PropertyValue:
    raw_value: str
    is_array: bool = False
    array_values: List[str] = field(default_factory=list)
    is_nested: bool = False
    nested_values: Dict[str, 'PropertyValue'] = field(default_factory=dict)

@dataclass(frozen=True)
class ClassInfo:
    name: str
    parent: Optional[str]
    properties: Dict[str, PropertyValue]
    source_file: Path
    config_type: str
    scope: int = 0
