from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
import re

class PropertyValueType(Enum):
    ARRAY = auto()
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    IDENTIFIER = auto()

@dataclass
class PropertyValue:
    raw_value: str
    value_type: PropertyValueType
    array_values: List[str] = None

    def __post_init__(self):
        if self.array_values is None:
            self.array_values = []

class PropertyTypeDetector:
    EMPTY_ARRAY_PATTERN = re.compile(r'^\s*{\s*}\s*$')
    ARRAY_PATTERN = re.compile(r'^\s*{(.*)}\s*$')
    STRING_PATTERN = re.compile(r'^"([^"]*)"$')
    NUMBER_PATTERN = re.compile(r'^-?\d+(\.\d+)?$')
    BOOLEAN_PATTERN = re.compile(r'^(true|false)$', re.IGNORECASE)

    @classmethod
    def detect_value_type(cls, value: str) -> PropertyValue:
        """Detect and parse property value type"""
        value = value.strip()
        
        # Check for empty array
        if cls.EMPTY_ARRAY_PATTERN.match(value):
            return PropertyValue(value, PropertyValueType.ARRAY, [])
            
        # Check for array
        if array_match := cls.ARRAY_PATTERN.match(value):
            array_content = array_match.group(1).strip()
            if not array_content:
                return PropertyValue(value, PropertyValueType.ARRAY, [])
            array_values = cls._parse_array_values(array_content)
            return PropertyValue(value, PropertyValueType.ARRAY, array_values)
            
        # Check for string
        if cls.STRING_PATTERN.match(value):
            return PropertyValue(value, PropertyValueType.STRING)
            
        # Check for number
        if cls.NUMBER_PATTERN.match(value):
            return PropertyValue(value, PropertyValueType.NUMBER)
            
        # Check for boolean
        if cls.BOOLEAN_PATTERN.match(value):
            return PropertyValue(value, PropertyValueType.BOOLEAN)
            
        # Default to identifier
        return PropertyValue(value, PropertyValueType.IDENTIFIER)

    @classmethod
    def _parse_array_values(cls, content: str) -> List[str]:
        """Parse array values handling nested structures"""
        values = []
        current = ''
        in_string = False
        string_char = None
        brace_level = 0
        
        for char in content:
            if char in '"\'':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                current += char
            elif char == '{' and not in_string:
                brace_level += 1
                current += char
            elif char == '}' and not in_string:
                brace_level -= 1
                current += char
            elif char == ',' and not in_string and brace_level == 0:
                values.append(current.strip())
                current = ''
            else:
                current += char
                
        if current:
            values.append(current.strip())
            
        return values
