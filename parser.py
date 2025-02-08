import re
from typing import Dict, Optional, Any, TypedDict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ClassData(TypedDict):
    parent: Optional[str]
    properties: Dict[str, Any]


class ClassParser:
    """Parser for class definitions in config files"""

    def __init__(self) -> None:
        self._prefix_cache: Dict[str, str] = {}
        self.current_file: Optional[Path] = None

    def parse_class_definitions(self, content: str) -> Dict[str, Any]:
        """Parse class definitions from config content"""
        result: Dict[str, Dict[str, ClassData]] = {
            'CfgPatches': {},
            'CfgWeapons': {},
            'CfgVehicles': {},
            'CfgModSettings': {},
            '_global': {}
        }

        current_section = '_global'
        current_class = None
        class_stack: list[str] = []

        content = self._clean_code(content)
        lines = content.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            if line.startswith('class '):
                class_def = line.split('class ', 1)[1]

                parts = class_def.split(':', 1)
                class_part = parts[0].strip()

                class_name = class_part.split('{')[0].strip() if '{' in class_part else class_part.strip()
                class_name = class_name.rstrip('{:;}')
                if class_name.endswith('{}'):
                    class_name = class_name[:-2]

                parent = ''
                if len(parts) > 1:
                    parent_part = parts[1].strip()
                    parent = parent_part.split('{')[0].strip() if '{' in parent_part else parent_part.strip()
                    parent = parent.rstrip('{:;}')
                    if parent.endswith('{}'):
                        parent = parent[:-2]

                class_data: ClassData = {
                    'parent': parent,
                    'properties': {}
                }

                if class_name in result:
                    current_section = class_name
                else:
                    if current_class:
                        class_stack.append(current_class)
                    current_class = class_name
                    result[current_section][class_name] = class_data

            elif line == '};':
                if class_stack:
                    current_class = class_stack.pop()
                elif current_class:
                    current_class = None

            i += 1

        return result

    def _clean_code(self, code: str) -> str:
        """Clean comments and whitespace from code"""
        text = re.sub(r'//.*?(?:\n|$)', '\n', code, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return re.sub(r'\n\s*\n', '\n', text)
