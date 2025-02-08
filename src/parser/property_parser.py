import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import re
from .property_tokenizer import PropertyTokenizer, PropertyTokenType, PropertyToken
from .property_types import PropertyTypeDetector, PropertyValueType

logger = logging.getLogger(__name__)


@dataclass
class PropertyData:
    value: str
    is_array: bool = False
    array_values: List[str] = field(default_factory=list)


class PropertyParser:
    def __init__(self):
        self.tokenizer = PropertyTokenizer()

    def parse_block_properties(self, block: str) -> Dict[str, PropertyData]:
        """Parse properties from a class block, skipping nested classes"""
        logger.debug("Starting to parse block:\n%s", block)
        
        # Extract inner block if full class definition is provided
        if block.strip().startswith('class'):
            block = self._extract_inner_block(block)
        
        block = self._preprocess_block(block)
        logger.debug("Processing inner block:\n%s", block)
        
        properties = {}
        current_line = ''
        depth = 1  # Start at depth 1 since we're inside a class block
        nested_class = False
        pos = 0
        
        while pos < len(block):
            char = block[pos]
            
            if char == '{':
                # Check for nested class
                if 'class' in current_line:
                    logger.debug("Found nested class start: %s", current_line)
                    nested_class = True
                    depth += 1
                    logger.debug("Depth increased to %d", depth)
                else:
                    # Add brace to current line if not a class
                    current_line += char
            elif char == '}':
                if nested_class and depth > 1:
                    depth -= 1
                    if depth == 1:
                        nested_class = False
                    logger.debug("Depth decreased to %d", depth)
                else:
                    # Add brace to current line if not end of nested class
                    current_line += char
            elif char == ';':
                current_line = (current_line + char).strip()
                # Process properties at base level and not in nested classes
                if '=' in current_line and not nested_class:
                    logger.debug("Processing property line: '%s'", current_line)
                    if prop := self._parse_property(current_line):
                        name, value, is_array, array_values = prop
                        logger.debug("Successfully parsed property: name='%s', value='%s', is_array=%s, values=%s",
                                   name, value, is_array, array_values)
                        properties[name] = PropertyData(
                            value=value,
                            is_array=is_array,
                            array_values=array_values
                        )
                    else:
                        logger.debug("Failed to parse as property: '%s'", current_line)
                current_line = ''
            else:
                current_line += char
            pos += 1

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
        # Convert to lowercase
        text = block.lower()
        
        # Remove comments
        text = re.sub(r'//.*?(?:\n|$)', ' ', text, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.DOTALL)
        
        # Preserve braces in empty arrays
        text = re.sub(r'=\s*{\s*}', '= {}', text)
        
        # Normalize whitespace
        text = ' '.join(line.strip() for line in text.splitlines())
        
        return text

    def _parse_property(self, line: str) -> Optional[Tuple[str, str, bool, List[str]]]:
        """Parse a property line into (name, value, is_array, array_values)"""
        logger.debug("Parsing property line: '%s'", line)
        tokens = list(self.tokenizer.tokenize(line))
        
        if not tokens:
            return None
            
        # Check for valid property structure
        if tokens[0].type != PropertyTokenType.IDENTIFIER:
            return None
            
        name = tokens[0].value
        is_array = False
        pos = 1
        
        # Check for array marker
        if pos < len(tokens) and tokens[pos].type == PropertyTokenType.ARRAY_MARKER:
            logger.debug("Found array marker for property: %s", name)
            is_array = True
            pos += 1
        
        # Handle empty array case
        if is_array and '{}' in line:
            return name, "{}", True, []
        
        # Expect equals sign
        if pos >= len(tokens) or tokens[pos].type != PropertyTokenType.EQUALS:
            return None
            
        # Get raw value by joining remaining tokens
        value_str = self._join_value_tokens(tokens[pos + 1:])
        if not value_str:
            # Special handling for empty arrays
            if is_array and any(t.type == PropertyTokenType.LBRACE for t in tokens[pos + 1:]):
                return name, "{}", True, []
            return None
            
        # Clean value (remove quotes)
        clean_value = self._clean_value(value_str)
        
        # Handle array properties
        if is_array:
            array_values = self._parse_array_content(clean_value)
            return name, clean_value, True, array_values
            
        return name, clean_value, False, []

    def _clean_value(self, value: str) -> str:
        """Clean a value by removing outer quotes if present"""
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        return value

    def _parse_array_content(self, value: str) -> List[str]:
        """Parse array content and clean individual values"""
        if value == '{}':
            return []
            
        if not (value.startswith('{') and value.endswith('}')):
            return [value]
            
        content = value[1:-1].strip()
        if not content:
            return []
            
        values = []
        for item in self._split_array_items(content):
            values.append(self._clean_value(item))
            
        return values

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
        
        # Look for opening brace
        if tokens[0].type != PropertyTokenType.LBRACE:
            return None, []
            
        # Handle empty array
        if len(tokens) >= 2 and tokens[1].type == PropertyTokenType.RBRACE:
            logger.debug("Found empty array")
            return "{}", []
            
        # Parse array contents
        values = []
        current = []
        depth = 0
        
        for token in tokens:
            if token.type == PropertyTokenType.SEMICOLON:
                break
                
            if token.type == PropertyTokenType.LBRACE:
                depth += 1
                if depth == 1:  # Skip outer braces in value collection
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
