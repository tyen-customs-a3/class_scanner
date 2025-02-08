import re
from typing import List, Dict, Any
from .tokenizer import Token, TokenType, CodeTokenizer

class CodeParser:
    def __init__(self):
        self.tokenizer = CodeTokenizer()
    
    def parse(self, content: str) -> Dict[str, Any]:
        """Main parsing entry point"""
        cleaned = self._preprocess_text(content)
        
        tokens = list(self.tokenizer.tokenize(cleaned))
        
        return self._parse_tokens(tokens)

    def _preprocess_text(self, content: str) -> str:
        """Clean up input text for parsing"""
        # Convert to lowercase first
        text = content.lower()
        
        # Remove comments
        text = re.sub(r'//.*?(?:\n|$)|\s+/\*.*?\*/\s+', ' ', text, flags=re.MULTILINE|re.DOTALL)
        
        # Clean up whitespace
        text = re.sub(r'\s*([{};])\s*', r'\1', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _parse_tokens(self, tokens: List[Token]) -> Dict[str, Any]:
        """Parse tokens into AST structure"""
        result = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type == TokenType.CLASS:
                class_name, class_data = self._parse_class_definition(tokens[i:])
                result[class_name] = class_data
                i += len(class_data.get('tokens_consumed', 0))
            i += 1
        return result

    def _parse_class_definition(self, tokens: List[Token]) -> tuple[str, Dict[str, Any]]:
        """Parse a class definition starting at the current token"""
        return "", {"properties": {}, "tokens_consumed": 1}
