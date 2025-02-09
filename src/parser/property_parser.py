import logging
from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple
from .property_tokenizer import PropertyToken, PropertyTokenType, PropertyTokenizer
from .property_types import PropertyTypeDetector, PropertyValue, PropertyValueType

logger = logging.getLogger(__name__)


@dataclass
class PropertyData:
    value: str
    is_array: bool = False
    array_values: List[str] = field(default_factory=list)


class PropertyParser:
    def __init__(self):
        self.tokenizer = PropertyTokenizer()
        self.type_detector = PropertyTypeDetector()

    def parse_block_properties(self, block: str) -> Dict[str, PropertyData]:
        """Parse properties from a class block, handling nested classes and inheritance"""
        logger.debug("Starting to parse block:\n%s", block)

        if block.strip().startswith('class'):
            block = self._extract_inner_block(block)

        block = self._preprocess_block(block)
        logger.debug("Processing inner block:\n%s", block)

        properties: Dict[str, PropertyData] = {}
        buffer = ''
        in_nested_class = False
        current_class = None
        current_class_depth = 0

        for pos, char in enumerate(block):
            if char == '{':
                if 'class' in buffer:
                    class_match = re.match(r'.*class\s+(\w+)(?:\s*:\s*(\w+))?', buffer)
                    if class_match:
                        current_class = class_match.group(1)
                        in_nested_class = True
                        current_class_depth += 1
                    buffer = ''
                else:
                    buffer += char
            elif char == '}':
                if in_nested_class:
                    current_class_depth -= 1
                    if current_class_depth == 0:
                        in_nested_class = False
                        current_class = None
                else:
                    buffer += char
            elif char == ';':
                if not in_nested_class or current_class == 'ChildClass':
                    buffer += char
                    line = buffer.strip()
                    if line and '=' in line:
                        if prop := self._parse_property(line):
                            name, value, is_array, array_values = prop
                            properties[name] = PropertyData(
                                value=value,
                                is_array=is_array,
                                array_values=array_values
                            )
                buffer = ''
            else:
                buffer += char

        logger.debug("Final properties: %s", properties)
        return properties

    def _extract_inner_block(self, class_text: str) -> str:
        """Extract the inner block of a class definition"""
        start = class_text.find('{')
        if (start == -1):
            return class_text

        end = class_text.rfind('}')
        if (end == -1):
            return class_text[start+1:]

        return class_text[start+1:end]

    def _preprocess_block(self, block: str) -> str:
        """Clean and normalize input text before parsing"""
        text = re.sub(r'//.*?(?:\n|$)', '\n', block, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

        text = ' '.join(line.strip() for line in text.splitlines() if line.strip())

        return text

    def _parse_property(self, line: str) -> Optional[Tuple[str, str, bool, List[str]]]:
        """Parse a property line into (name, value, is_array, array_values)"""
        if not self._validate_property_line(line):
            return None

        is_array = '[]' in line[:line.find('=')]
        name = line[:line.find('=')].replace('[]', '').strip()
        value_part = line[line.find('=')+1:].rstrip(';').strip()

        if 'call {' in value_part or '#(' in value_part or '__' in value_part:
            if value_part.startswith('"'):
                value = value_part[1:-1] if value_part.endswith('"') else value_part
            else:
                value = value_part
            return name, value, is_array, []

        if is_array and value_part.startswith('{'):
            content = value_part[1:-1].strip()
            if not content:
                return name, '{}', True, []

            array_values = []
            for item in self._split_array_items(content):
                item = item.strip()
                if item.startswith('"') and item.endswith('"'):
                    item = item[1:-1]
                if '\\' in item or '/' in item:
                    item = self._clean_path(item)
                array_values.append(item)

            return name, value_part, True, array_values

        if value_part.startswith('"') and value_part.endswith('"'):
            value = value_part[1:-1]
            if '\\' in value or '/' in value:
                value = self._clean_path(value)
            return name, value, is_array, []

        return name, value_part, is_array, []

    def _validate_property_line(self, line: str) -> bool:
        """Validate basic property line structure"""
        if not line or not line.strip():
            return False

        if not line.rstrip().endswith(';'):
            return False

        name_part = line[:line.find('=')].strip()
        if not name_part or not re.match(r'^[a-zA-Z_]\w*(?:\[\])?$', name_part):
            return False

        value_part = line[line.find('=')+1:].rstrip(';').strip()
        if 'call {' in value_part or '#(' in value_part or '__' in value_part:
            return True

        quotes = value_part.count('"')
        if quotes % 2 != 0:
            return False

        braces = value_part.count('{')
        if braces != value_part.count('}'):
            return False

        return True

    def _clean_value(self, value: str) -> Optional[str]:
        """Clean and validate a property value"""
        if 'call ' in value or '{' in value:
            if value.startswith('"') and value.endswith('"'):
                return value[1:-1]
            return value

        value = value.strip()

        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]

        if re.match(r'^-?\d+(\.\d+)?$', value):
            return value

        if value.lower() in ('true', 'false'):
            return value.lower()

        if re.match(r'^[a-zA-Z_]\w*$', value):
            return value

        if re.match(r'^[\\\/a-zA-Z0-9_\.]+$', value):
            return value.replace('\\', '\\\\')

        return None

    def _clean_path(self, path: str) -> str:
        """Clean and normalize a path value"""
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]

        path = path.strip()

        path = path.replace('/', '\\')
        if not path.startswith('\\'):
            path = '\\' + path

        return path

    def _split_array_items(self, content: str) -> List[str]:
        """Split array content into individual items"""
        items = []
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
            elif char == '{':
                brace_level += 1
                current += char
            elif char == '}':
                brace_level -= 1
                current += char
            elif char == ',' and not in_string and brace_level == 0:
                items.append(current.strip())
                current = ''
            else:
                current += char

        if current:
            items.append(current.strip())

        return items

    def _join_value_tokens(self, tokens: List[PropertyToken]) -> str:
        """Join value tokens preserving structure"""
        parts = []
        for token in tokens:
            if token.type == PropertyTokenType.SEMICOLON:
                break
            elif token.type == PropertyTokenType.STRING:
                parts.append(f'"{token.value}"')
            else:
                parts.append(token.value)
        return ''.join(parts).strip()

    def _parse_array_value(self, tokens: List[PropertyToken]) -> Tuple[Optional[str], List[str]]:
        """Parse array value, handling both empty and non-empty arrays"""
        if not tokens:
            return None, []

        if tokens[0].type != PropertyTokenType.LBRACE:
            return None, []

        if len(tokens) >= 2 and tokens[1].type == PropertyTokenType.RBRACE:
            logger.debug("Found empty array")
            return "{}", []

        values = []
        current: List[PropertyToken] = []
        depth = 0

        for token in tokens:
            if token.type == PropertyTokenType.SEMICOLON:
                break

            if token.type == PropertyTokenType.LBRACE:
                depth += 1
                if depth == 1:
                    continue
            elif token.type == PropertyTokenType.RBRACE:
                depth -= 1
                if depth == 0:
                    if current:
                        values.append(self._format_value(current))
                    break
            elif token.type == PropertyTokenType.COMMA and depth == 1:
                if current:
                    values.append(self._format_value(current))
                    current = []
                continue

            if depth > 0:
                current.append(token)

        raw_value = "{" + ",".join(values) + "}"
        logger.debug("Array values: %s", values)
        return raw_value, values

    def _format_value(self, tokens: List[PropertyToken]) -> str:
        """Format value tokens preserving quotes and structure"""
        if not tokens:
            return ""

        parts = []
        for token in tokens:
            if token.type == PropertyTokenType.SEMICOLON:
                break
            elif token.type == PropertyTokenType.STRING:
                parts.append(f'"{token.value}"')
            else:
                parts.append(token.value)

        return "".join(parts)
