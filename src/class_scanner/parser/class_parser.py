import re
from typing import Dict, Optional, Any, cast, Tuple, TypeVar, Union
from pathlib import Path
import logging

from class_scanner.models import (
    ClassDict, ConfigSections, SectionDict, 
    ClassSectionsDict
)
from class_scanner.parser.property_parser import PropertyParser
from ..constants import ConfigSectionName, CFG_PATCHES, CFG_WEAPONS, CFG_VEHICLES, CFG_GLOBAL

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ClassParser:
    """Parser for class definitions in config files"""
    
    def __init__(self) -> None:
        self._prefix_cache: Dict[str, str] = {}
        self.current_file: Optional[Path] = None
        self.property_parser = PropertyParser()

    def _get_section_dict(self, result: ConfigSections, section: ConfigSectionName) -> SectionDict:
        if section not in result:
            result[section] = {}
        return result[section]

    def _determine_section(self, class_name: str, parent: str, current_section: Optional[ConfigSectionName] = None) -> Optional[ConfigSectionName]:
        """Determine which section a class belongs to"""
        # Explicit config sections take precedence
        if class_name.startswith('Cfg'):
            if class_name in (CFG_PATCHES, CFG_WEAPONS, CFG_VEHICLES):
                return cast(ConfigSectionName, class_name)
        
        # Use current section if we're inside one
        if current_section:
            return current_section
            
        # Default to global section for loose classes
        return CFG_GLOBAL

    def parse_class_definitions(self, content: str) -> ClassSectionsDict:
        """Parse class definitions and their properties"""
        logger.debug("Starting class definitions parsing")
        # Initialize with just global section
        result: ConfigSections = {
            CFG_GLOBAL: {}
        }

        # Only add other sections when they're found in the data
        def ensure_section(section: ConfigSectionName) -> None:
            if section not in result:
                result[section] = {}

        content = self._clean_code(content)
        current_section: Optional[ConfigSectionName] = None
        logger.debug("Cleaned content length: %d", len(content))

        def parse_block(text: str, start: int, container: str = '', parent_section: Optional[ConfigSectionName] = None) -> Tuple[Dict[str, Dict[str, Any]], int]:
            """Parse a block of class definitions recursively"""
            logger.debug("Parsing block - Container: %s, Parent Section: %s", container, parent_section)
            classes: Dict[str, Dict[str, Any]] = {}
            pos = start

            while pos < len(text):
                match = re.search(r'class\s+(\w+)(?:\s*:\s*(\w+))?\s*({|;)', text[pos:])
                if not match:
                    break

                class_name = match.group(1)
                parent = match.group(2) or ''
                has_block = match.group(3) == '{'
                
                # Determine section based on class name and context
                target_section = self._determine_section(class_name, parent, parent_section or current_section)
                logger.debug("Found class: %s, Parent: %s, Target Section: %s", 
                           class_name, parent, target_section)

                if has_block:
                    block_start = pos + match.end() - 1
                    block, block_end = self._extract_class_block(text, block_start)
                    logger.debug("Extracted block for %s, length: %d", class_name, len(block))
                    
                    properties = self.property_parser.parse_block_properties(block)
                    
                    # Add to appropriate section
                    if target_section:
                        ensure_section(target_section)
                        section_dict = self._get_section_dict(result, target_section)
                        section_dict[class_name] = ClassDict(
                            parent=parent,
                            properties=properties,
                            container=container
                        )

                    # Parse nested classes with inherited section
                    nested_section = target_section if class_name.startswith('Cfg') else None
                    nested_classes, _ = parse_block(block, 0, class_name, nested_section)

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

        return cast(ClassSectionsDict, result)

    def _clean_code(self, code: str) -> str:
        """Clean comments and whitespace from code"""
        text = re.sub(r'//.*?(?:\n|$)', '\n', code, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return re.sub(r'\n\s*\n', '\n', text)

    def _extract_class_block(self, content: str, start_pos: int) -> Tuple[str, int]:
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
