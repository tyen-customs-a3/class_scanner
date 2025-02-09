from enum import auto
import re
from typing import List, Optional, Tuple
from ..models.core import PropertyValue, PropertyValueType
from .property_tokenizer import PropertyToken, PropertyTokenType

class PropertyTypeDetector:
    EMPTY_ARRAY_PATTERN = re.compile(r'^\s*{\s*}\s*$')
    ARRAY_PATTERN = re.compile(r'^\s*{(.*)}\s*$')
    STRING_PATTERN = re.compile(r'^"([^"]*)"$')
    NUMBER_PATTERN = re.compile(r'^-?\d+(\.\d+)?$')
    BOOLEAN_PATTERN = re.compile(r'^(true|false)$', re.IGNORECASE)

    def detect_value(self, tokens: List[PropertyToken]) -> Optional[PropertyValue]:
        """Detect and extract property value from tokens"""
        result = PropertyValue()
        
        # Extract name
        name_tokens = self._extract_name_tokens(tokens)
        if not name_tokens:
            return None
        result.name = name_tokens[0].value
        
        # Handle array marker
        result.value_type = PropertyValueType.ARRAY if any(t.type == PropertyTokenType.ARRAY_MARKER for t in name_tokens) else None
        
        # Extract value
        value_tokens = self._extract_value_tokens(tokens)
        if not value_tokens:
            return None
            
        value_type, raw_value, array_values = self._parse_value(value_tokens)
        result.value_type = value_type
        result.raw_value = raw_value
        result.array_values = array_values
        
        return result

    def _extract_name_tokens(self, tokens: List[PropertyToken]) -> List[PropertyToken]:
        """Extract property name tokens"""
        name_tokens = []
        for token in tokens:
            if token.type == PropertyTokenType.EQUALS:
                break
            name_tokens.append(token)
        return name_tokens

    def _extract_value_tokens(self, tokens: List[PropertyToken]) -> List[PropertyToken]:
        """Extract property value tokens"""
        value_tokens = []
        found_equals = False
        
        for token in tokens:
            if token.type == PropertyTokenType.EQUALS:
                found_equals = True
                continue
            if found_equals:
                if token.type == PropertyTokenType.SEMICOLON:
                    break
                value_tokens.append(token)
                
        return value_tokens

    def _parse_value(self, tokens: List[PropertyToken]) -> Tuple[PropertyValueType, str, List[str]]:
        """Parse value tokens into type, raw value and array values"""
        if not tokens:
            return PropertyValueType.IDENTIFIER, '', []

        # Handle array values
        if tokens[0].type == PropertyTokenType.LBRACE:
            array_values = []
            current_value = []
            brace_depth = 0
            
            for token in tokens:
                if token.type == PropertyTokenType.LBRACE:
                    brace_depth += 1
                    if brace_depth > 1:
                        current_value.append(token)
                elif token.type == PropertyTokenType.RBRACE:
                    brace_depth -= 1
                    if brace_depth == 0:
                        if current_value:
                            array_values.append(self._format_token_value(current_value))
                    else:
                        current_value.append(token)
                elif token.type == PropertyTokenType.COMMA and brace_depth == 1:
                    if current_value:
                        array_values.append(self._format_token_value(current_value))
                        current_value = []
                else:
                    current_value.append(token)
                    
            raw_value = '{' + ', '.join(array_values) + '}'
            return PropertyValueType.ARRAY, raw_value, array_values

        # Handle other value types
        if tokens[0].type == PropertyTokenType.STRING:
            return PropertyValueType.STRING, tokens[0].value, []
        elif tokens[0].type == PropertyTokenType.NUMBER:
            return PropertyValueType.NUMBER, tokens[0].value, []
        elif tokens[0].type == PropertyTokenType.BOOLEAN:
            return PropertyValueType.BOOLEAN, tokens[0].value, []
            
        # Default to identifier
        return PropertyValueType.IDENTIFIER, tokens[0].value, []

    def _format_token_value(self, tokens: List[PropertyToken]) -> str:
        """Format a list of tokens into a string value"""
        parts = []
        for token in tokens:
            if token.type == PropertyTokenType.STRING:
                parts.append(f'"{token.value}"')
            else:
                parts.append(token.value)
        return ''.join(parts).strip()

    @classmethod
    def detect_value_type(cls, value: str) -> PropertyValue:
        """Detect and parse property value type"""
        value = value.strip()

        if cls.EMPTY_ARRAY_PATTERN.match(value):
            return PropertyValue(
                raw_value=value,
                value_type=PropertyValueType.ARRAY,
                is_array=True,
                array_values=[]
            )

        if array_match := cls.ARRAY_PATTERN.match(value):
            array_content = array_match.group(1).strip()
            if not array_content:
                return PropertyValue(
                    raw_value=value,
                    value_type=PropertyValueType.ARRAY,
                    is_array=True,
                    array_values=[]
                )
            array_values = cls._parse_array_values(array_content)
            return PropertyValue(
                raw_value=value,
                value_type=PropertyValueType.ARRAY,
                is_array=True,
                array_values=array_values
            )

        # Handle other value types
        if cls.STRING_PATTERN.match(value):
            return PropertyValue(raw_value=value, value_type=PropertyValueType.STRING)
        elif cls.NUMBER_PATTERN.match(value):
            return PropertyValue(raw_value=value, value_type=PropertyValueType.NUMBER)
        elif cls.BOOLEAN_PATTERN.match(value):
            return PropertyValue(raw_value=value, value_type=PropertyValueType.BOOLEAN)

        return PropertyValue(raw_value=value, value_type=PropertyValueType.IDENTIFIER)

    @classmethod
    def _parse_array_values(cls, content: str) -> List[str]:
        """Parse array values handling nested structures"""
        values = []
        current = ''
        depth = 0
        in_string = False
        string_char = None

        for char in content:
            if char in '"\'':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                current += char
            elif char == '{':
                depth += 1
                current += char
            elif char == '}':
                depth -= 1
                current += char
            elif char == ',' and depth == 0 and not in_string:
                if current:
                    values.append(current.strip())
                current = ''
            else:
                current += char

        if current:
            values.append(current.strip())

        return values
