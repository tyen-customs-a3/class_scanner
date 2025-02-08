from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator

class TokenType(Enum):
    CLASS = auto()
    IDENTIFIER = auto()
    EQUALS = auto()
    ARRAY_START = auto()
    ARRAY_END = auto()
    BLOCK_START = auto()
    BLOCK_END = auto()
    SEMICOLON = auto()
    STRING = auto()
    NUMBER = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    position: int

class CodeTokenizer:
    def tokenize(self, text: str) -> Iterator[Token]:
        pos = 0
        while pos < len(text):
            char = text[pos]
            
            # Skip whitespace
            if char.isspace():
                pos += 1
                continue
            
            # Skip comments
            if char == '/' and pos + 1 < len(text):
                if text[pos + 1] == '/':
                    pos = text.find('\n', pos)
                    if pos == -1:
                        break
                    continue
                elif text[pos + 1] == '*':
                    end = text.find('*/', pos)
                    if end == -1:
                        break
                    pos = end + 2
                    continue
                
            # Match keywords and symbols
            if char == '{':
                yield Token(TokenType.BLOCK_START, '{', pos)
            elif char == '}':
                yield Token(TokenType.BLOCK_END, '}', pos)
            elif char == '[':
                yield Token(TokenType.ARRAY_START, '[', pos)
            elif char == ']':
                yield Token(TokenType.ARRAY_END, ']', pos)
            elif char == '=':
                yield Token(TokenType.EQUALS, '=', pos)
            elif char == ';':
                yield Token(TokenType.SEMICOLON, ';', pos)
            elif char == '"' or char == "'":
                end = text.find(char, pos + 1)
                if end == -1:
                    break
                yield Token(TokenType.STRING, text[pos+1:end], pos)
                pos = end + 1
                continue
            elif char.isdigit():
                num = ''
                while pos < len(text) and (text[pos].isdigit() or text[pos] == '.'):
                    num += text[pos]
                    pos += 1
                yield Token(TokenType.NUMBER, num, pos - len(num))
                continue
            elif char.isalpha() or char == '_':
                word = ''
                while pos < len(text) and (text[pos].isalnum() or text[pos] == '_'):
                    word += text[pos]
                    pos += 1
                token_type = TokenType.CLASS if word == 'class' else TokenType.IDENTIFIER
                yield Token(token_type, word, pos - len(word))
                continue
            
            pos += 1
