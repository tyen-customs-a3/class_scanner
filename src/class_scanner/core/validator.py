from typing import List, Set, Dict
from pathlib import Path
from ..models import ClassInfo, ValidationResult, ValidationIssue

class ClassValidator:
    """Dedicated validator for class definitions"""
    
    def validate_inheritance(self, class_info: ClassInfo, 
                           available_classes: Set[str]) -> List[str]:
        """Validate class inheritance"""
        issues = []
        current = class_info.parent
        visited = {class_info.name}
        
        while current:
            if current not in available_classes:
                issues.append(f"Unknown parent class: {current}")
                break
            if current in visited:
                issues.append(f"Circular inheritance detected: {current}")
                break
            visited.add(current)
            current = available_classes[current].parent
            
        return issues

    def validate_properties(self, properties: Dict[str, str], 
                          required_props: Set[str]) -> List[str]:
        """Validate required properties exist"""
        missing = required_props - set(properties)
        return [f"Missing required property: {prop}" for prop in missing]
