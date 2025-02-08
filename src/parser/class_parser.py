import re
from typing import Dict, Optional, Any, TypedDict, cast, Union, Mapping
from pathlib import Path
import logging
from .property_parser import PropertyParser
from ..constants import (
    ConfigSectionName,
    CFG_PATCHES,
    CFG_WEAPONS,
    CFG_VEHICLES,
    CFG_GLOBAL,
    ALL_CONFIG_SECTIONS
)

logger = logging.getLogger(__name__)


class ClassData(TypedDict):
    parent: str
    properties: Dict[str, Any]


class ConfigSections(TypedDict):
    CfgPatches: Dict[str, ClassData]
    CfgWeapons: Dict[str, ClassData]
    CfgVehicles: Dict[str, ClassData]
    _global: Dict[str, ClassData]


class ClassParser:
    """Parser for class definitions in config files"""

    def __init__(self) -> None:
        self._prefix_cache: Dict[str, str] = {}
        self.current_file: Optional[Path] = None
        self.property_parser = PropertyParser()

    def _get_section_dict(self, result: ConfigSections, section: ConfigSectionName) -> Dict[str, ClassData]:
        """Helper method to access section dictionaries with type safety"""
        return result[section]

    def parse_class_definitions(self, content: str) -> ConfigSections:
        """Parse class definitions and their properties"""
        result: ConfigSections = {
            CFG_PATCHES: {},
            CFG_WEAPONS: {},
            CFG_VEHICLES: {},
            CFG_GLOBAL: {}
        }
        
        content = self._clean_code(content)
        current_section: Optional[ConfigSectionName] = None
        
        base_classes = re.finditer(r'class\s+(\w+)\s*;', content)
        for match in base_classes:
            class_name = match.group(1)
            global_dict = self._get_section_dict(result, CFG_GLOBAL)
            global_dict[class_name] = ClassData(parent='', properties={})
        
        def parse_block(text: str, start: int) -> tuple[Dict[str, Any], int]:
            """Parse a block of class definitions recursively"""
            classes = {}
            pos = start
            
            while pos < len(text):
                match = re.search(r'class\s+(\w+)(?:\s*:\s*(\w+))?\s*({|;)', text[pos:])
                if not match:
                    break
                    
                class_name = match.group(1)
                parent = match.group(2) or ''
                has_block = match.group(3) == '{'
                
                if has_block:
                    block_start = pos + match.end() - 1
                    block, block_end = self._extract_class_block(text, block_start)
                    
                    nested_classes, _ = parse_block(block, 0)
                    properties = self.property_parser.parse_block_properties(block)
                    
                    pos = block_end + 1
                else:
                    properties = {}
                    nested_classes = {}
                    pos += match.end()
                
                classes[class_name] = {
                    'parent': parent,
                    'properties': properties,
                    'nested': nested_classes
                }
            
            return classes, pos

        all_classes, _ = parse_block(content, 0)
        
        for class_name, class_data in all_classes.items():
            if class_name in (CFG_PATCHES, CFG_WEAPONS, CFG_VEHICLES):
                section = cast(ConfigSectionName, class_name)
                section_dict = self._get_section_dict(result, section)
                section_dict.update(class_data['nested'])
                
                for nested_name, nested_data in class_data['nested'].items():
                    parent = nested_data.get('parent')
                    if parent and parent in self._get_section_dict(result, CFG_GLOBAL):
                        base_class = parent
                        global_dict = self._get_section_dict(result, CFG_GLOBAL)
                        if base_class in global_dict:
                            section_dict[base_class] = global_dict.pop(base_class)
                current_section = section
            else:
                target_section = current_section if current_section else CFG_GLOBAL
                self._get_section_dict(result, target_section)[class_name] = ClassData(
                    parent=class_data['parent'],
                    properties=class_data['properties']
                )
                
        return result

    def _clean_code(self, code: str) -> str:
        """Clean comments and whitespace from code"""
        text = re.sub(r'//.*?(?:\n|$)', '\n', code, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return re.sub(r'\n\s*\n', '\n', text)

    def _extract_class_block(self, content: str, start_pos: int) -> tuple[str, int]:
        """Extract a single class block without parsing nested classes"""
        depth = 0
        end_pos = start_pos
        in_string = False
        string_char = None
        
        while end_pos < len(content):
            char = content[end_pos]
            
            if char in '"\'':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                end_pos += 1
                continue
                
            if not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        return content[start_pos:end_pos+1], end_pos
            
            end_pos += 1
            
        return content[start_pos:end_pos], end_pos
