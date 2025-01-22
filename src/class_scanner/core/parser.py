import re
from typing import Dict, Optional, Tuple, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ClassParser:
    """Dedicated class for parsing class definitions"""
    
    def __init__(self):
        self._prefix_cache: Dict[str, str] = {}

    def parse_class_definitions(self, code: str, pbo_prefix: Optional[str] = None) -> Dict[str, Dict]:
        """Parse class definitions with improved property handling"""
        # Clean up code comments
        text = self._clean_code(code)
        root_prefix = self._find_root_prefix(text) or pbo_prefix
        
        return self._parse_class_block(text, root_prefix=root_prefix)

    def _clean_code(self, code: str) -> str:
        """Clean comments and whitespace from code"""
        text = re.sub(r'//.*?(?:\n|$)', '\n', code, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return re.sub(r'\n\s*\n', '\n', text)

    def _find_root_prefix(self, text: str) -> Optional[str]:
        """Find root prefix definition in code"""
        prefix_match = re.search(r'^\s*prefix\s*=\s*"([^"]+)"\s*;', text, re.MULTILINE)
        return prefix_match.group(1).replace('\\', '/') if prefix_match else None

    def _extract_class_content(self, text: str, start: int) -> Tuple[int, str]:
        """Extract content between balanced braces"""
        level = 0
        content_start = None
        
        for i in range(start, len(text)):
            if text[i] == '{':
                level += 1
                if level == 1:
                    content_start = i + 1
            elif text[i] == '}':
                level -= 1
                if level == 0 and content_start is not None:
                    return i, text[content_start:i]
                    
        return -1, ""

    def _parse_class_block(self, text: str, pos: int = 0, root_prefix: Optional[str] = None) -> Dict[str, Dict]:
        """Parse class block and nested classes"""
        result = {}
        base_props = {'prefix': root_prefix} if root_prefix else {}

        class_pattern = r'(?:class|enum)\s+(\w+)(?:\s*:\s*(?:public\s+)?([^\s{]+))?\s*{'
        
        while True:
            match = re.search(class_pattern, text[pos:], re.MULTILINE)
            if not match:
                break
                
            start_pos = pos + match.start()
            class_pos = pos + match.end()
            end_pos, content = self._extract_class_content(text, class_pos - 1)
            
            if end_pos == -1:
                break

            name = match.group(1)
            parent = match.group(2)
            is_enum = match.group(0).lstrip().startswith('enum')
            
            # Only collect raw properties without inheritance processing
            properties = dict(base_props)
            
            if is_enum:
                properties.update(self._parse_enum_values(content))
            else:
                properties.update(self.parse_properties(content))
                nested = self._parse_class_block(content, root_prefix=properties.get('prefix'))
                for nested_name, nested_info in nested.items():
                    if 'properties' in nested_info:
                        properties[nested_name] = nested_info['properties']

            result[name] = {
                'parent': parent.strip() if parent else None,
                'properties': properties,
                'type': 'enum' if is_enum else 'class'
            }
            
            pos = end_pos + 1

        return result

    def _parse_enum_values(self, content: str) -> Dict[str, str]:
        """Parse enum value definitions"""
        enum_pattern = r'(\w+)\s*=\s*([^,\s}]+)'
        return {
            match.group(1): match.group(2).strip()
            for match in re.finditer(enum_pattern, content)
        }

    def parse_properties(self, content: str) -> Dict[str, str]:
        """Parse class properties including arrays"""
        properties = {}
        prop_pattern = r'''
            (\w+)               # Property name
            (?:\[\])?          # Optional array marker
            \s*=\s*            # Equals with whitespace
            (?:
                \{             # Array start
                ([^}]+)        # Array contents
                \}             # Array end
                |              # OR
                ([^;]+)        # Regular value
            )
            \s*;              # End with semicolon
        '''
        
        for match in re.finditer(prop_pattern, content, re.VERBOSE | re.MULTILINE | re.DOTALL):
            name = match.group(1)
            array_value = match.group(2)
            single_value = match.group(3)
            
            if array_value is not None:
                items = [v.strip(' "\'') for v in array_value.split(',')]
                value = ','.join(v for v in items if v)
            else:
                value = single_value.strip(' "\'')
                
            properties[name.strip()] = value

        return properties

    def validate_syntax(self, code: str) -> List[str]:
        """Validate class definition syntax"""
        errors = []
        try:
            text = self._clean_code(code)
            # Check for basic syntax errors
            patterns = [
                (r'{[^}]*$', 'Unclosed brace'),
                (r'class\s*\w+\s*[^{;]*$', 'Incomplete class definition'),
                (r'=\s*[^;{]*$', 'Missing semicolon'),
                (r':\s*$', 'Missing parent class name')
            ]
            
            for pattern, error in patterns:
                if re.search(pattern, text, re.MULTILINE):
                    errors.append(error)
                    
        except Exception as e:
            errors.append(f"Syntax validation error: {e}")
            
        return errors
