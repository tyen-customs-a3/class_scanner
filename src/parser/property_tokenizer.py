from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, Optional


class PropertyTokenType(Enum):
    IDENTIFIER = auto()
    ARRAY_MARKER = auto()
    EQUALS = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    SEMICOLON = auto()
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()


@dataclass
class PropertyToken:
    type: PropertyTokenType
    value: str
    pos: int


class PropertyTokenizer:
    def tokenize(self, text: str) -> Iterator[PropertyToken]:
        pos = 0
        text_len = len(text)
        
        while pos < text_len:
            char = text[pos]
            
            # Skip whitespace
            if char.isspace():
                pos += 1
                continue
                
            # Handle special characters
            if char == '[':
                if pos + 1 < text_len and text[pos + 1] == ']':
                    yield PropertyToken(PropertyTokenType.ARRAY_MARKER, '[]', pos)
                    pos += 2
                    continue
            elif char == '=':
                yield PropertyToken(PropertyTokenType.EQUALS, '=', pos)
            elif char == '{':
                yield PropertyToken(PropertyTokenType.LBRACE, '{', pos)
            elif char == '}':
                yield PropertyToken(PropertyTokenType.RBRACE, '}', pos)
            elif char == ',':
                yield PropertyToken(PropertyTokenType.COMMA, ',', pos)
            elif char == ';':
                yield PropertyToken(PropertyTokenType.SEMICOLON, ';', pos)
            elif char in '"\'':
                string_value, new_pos = self._extract_string(text, pos)
                if string_value is not None:
                    yield PropertyToken(PropertyTokenType.STRING, string_value, pos)
                    pos = new_pos
                    continue
            elif char.isdigit() or char == '-':
                number, new_pos = self._extract_number(text, pos)
                if number is not None:
                    yield PropertyToken(PropertyTokenType.NUMBER, number, pos)
                    pos = new_pos
                    continue
            elif char.isalpha() or char == '_':
                identifier, new_pos = self._extract_identifier(text, pos)
                if identifier.lower() in ('true', 'false'):
                    yield PropertyToken(PropertyTokenType.BOOLEAN, identifier.lower(), pos)
                else:
                    yield PropertyToken(PropertyTokenType.IDENTIFIER, identifier, pos)
                pos = new_pos
                continue
            
            pos += 1

    def _extract_string(self, text: str, start: int) -> tuple[Optional[str], int]:
        quote = text[start]
        pos = start + 1
        value = ''
        
        while pos < len(text):
            char = text[pos]
            if char == quote:
                return value, pos + 1
            value += char
            pos += 1
            
        return None, start + 1

    def _extract_number(self, text: str, start: int) -> tuple[Optional[str], int]:
        pos = start
        value = ''
        has_decimal = False
        
        while pos < len(text):
            char = text[pos]
            if char.isdigit():
                value += char
            elif char == '.' and not has_decimal:
                value += char
                has_decimal = True
            else:
                break
            pos += 1
            
        return value if value else None, pos

    def _extract_identifier(self, text: str, start: int) -> tuple[str, int]:
        pos = start
        value = ''
        
        while pos < len(text) and (text[pos].isalnum() or text[pos] == '_'):
            value += text[pos]
            pos += 1
            
        return value, pos
