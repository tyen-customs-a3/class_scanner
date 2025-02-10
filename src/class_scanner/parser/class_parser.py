import re
from typing import Dict, Optional, Any, cast, Union, List, Tuple, Literal
from pathlib import Path
import logging

from class_scanner.models.core import ClassDict, ConfigSections
from class_scanner.parser.property_parser import PropertyParser
from ..constants import ConfigSectionName, CFG_PATCHES, CFG_WEAPONS, CFG_VEHICLES, CFG_GLOBAL

logger = logging.getLogger(__name__)


class ClassParser:
    """Parser for class definitions in config files"""

    def __init__(self) -> None:
        self._prefix_cache: Dict[str, str] = {}
        self.current_file: Optional[Path] = None
        self.property_parser = PropertyParser()

    def _get_section_dict(self, result: ConfigSections, section: ConfigSectionName) -> Dict[str, ClassDict]:
        """Helper method to access section dictionaries with type safety"""
        return result[section]

    def parse_class_definitions(self, content: str) -> ConfigSections:
        """Parse class definitions and their properties"""
        logger.debug("Starting class definitions parsing")
        result: ConfigSections = {
            CFG_PATCHES: {},
            CFG_WEAPONS: {},
            CFG_VEHICLES: {},
            CFG_GLOBAL: {}
        }

        content = self._clean_code(content)
        current_section: Optional[ConfigSectionName] = None
        logger.debug("Cleaned content length: %d", len(content))

        def parse_block(text: str, start: int, container: str = '', parent_section: Optional[ConfigSectionName] = None) -> tuple[Dict[str, Any], int]:
            """Parse a block of class definitions recursively"""
            logger.debug("Parsing block - Container: %s, Parent Section: %s", container, parent_section)
            classes = {}
            pos = start

            while pos < len(text):
                match = re.search(r'class\s+(\w+)(?:\s*:\s*(\w+))?\s*({|;)', text[pos:])
                if not match:
                    break

                class_name = match.group(1)
                parent = match.group(2) or ''
                has_block = match.group(3) == '{'
                
                logger.debug("Found class: %s, Parent: %s, Has Block: %s", class_name, parent, has_block)

                if has_block:
                    block_start = pos + match.end() - 1
                    block, block_end = self._extract_class_block(text, block_start)
                    logger.debug("Extracted block for %s, length: %d", class_name, len(block))
                    
                    properties = self.property_parser.parse_block_properties(block)
                    
                    target_section = parent_section if parent_section else current_section
                    if target_section and target_section in (CFG_PATCHES, CFG_WEAPONS, CFG_VEHICLES, CFG_GLOBAL):
                        section_dict = self._get_section_dict(result, target_section)
                        section_dict[class_name] = ClassDict(
                            parent=parent,
                            properties=properties,
                            container=container
                        )

                    logger.debug("Parsing nested classes for %s as container", class_name)
                    nested_classes, _ = parse_block(block, 0, class_name, target_section)

                    classes[class_name] = {
                        'parent': parent,
                        'properties': properties,
                        'nested': nested_classes,
                        'container': container
                    }

                    pos = block_end + 1
                else:
                    pos += match.end()
                    logger.debug("Added empty class %s", class_name)
                    classes[class_name] = {
                        'parent': parent,
                        'properties': {},
                        'nested': {},
                        'container': container
                    }

            return classes, pos

        logger.debug("Starting root level parsing")
        all_classes, _ = parse_block(content, 0)
        logger.debug("Found top-level classes: %s", list(all_classes.keys()))

        for class_name, class_data in all_classes.items():
            if class_name in (CFG_PATCHES, CFG_WEAPONS, CFG_VEHICLES):
                section = cast(ConfigSectionName, class_name)
                current_section = section
                section_dict = self._get_section_dict(result, section)
                
                def add_nested_classes(nested_data: Dict[str, Any], container: str) -> None:
                    for nested_name, nested_info in nested_data.items():
                        section_dict[nested_name] = ClassDict(
                            parent=nested_info['parent'],
                            properties=nested_info['properties'],
                            container=container
                        )
                        logger.debug("Added nested class %s to section %s with container %s",
                                   nested_name, section, container)
                        
                        if nested_info['nested']:
                            add_nested_classes(nested_info['nested'], nested_name)
                
                add_nested_classes(class_data['nested'], class_name)

        logger.debug("Finished parsing. Sections summary:")
        for section_name, section_dict in result.items():
            logger.debug("%s: %d classes", section_name, len(section_dict))
            for class_name, class_data in section_dict.items():
                logger.debug("  - %s (container: %s)", class_name, class_data['container'])

        return result

    def _clean_code(self, code: str) -> str:
        """Clean comments and whitespace from code"""
        text = re.sub(r'//.*?(?:\n|$)', '\n', code, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return re.sub(r'\n\s*\n', '\n', text)

    def _extract_class_block(self, content: str, start_pos: int) -> tuple[str, int]:
        """Extract a single class block without parsing nested classes"""
        logger.debug("Extracting class block from position %d", start_pos)
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
