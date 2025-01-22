import logging
from pathlib import Path
import re
from typing import Dict, Optional, List, Set, Callable, Tuple
from .models import ClassHierarchy, ClassInfo, UnprocessedClasses, RawClassDef
from .pbo_extractor import PboExtractor
from .core.parser import ClassParser

logger = logging.getLogger(__name__)

class ClassScanner:
    """Scanner for class definitions and hierarchies"""
    
    CODE_EXTENSIONS = {'.cpp', '.hpp', '.h', '.sqf', '.bin'}
    
    def __init__(self):
        self.pbo_extractor = PboExtractor()
        self.parser = ClassParser()
        self.pbo_extractor.CODE_EXTENSIONS = self.CODE_EXTENSIONS
        self._progress_callback = None

    def set_progress_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """Set the progress callback function
        
        Args:
            callback: Function that takes a file path string and returns None
        """
        self._progress_callback = callback

    def scan_classes(self, source: str, code_files: Dict[str, str]) -> UnprocessedClasses:
        """Scan code files and return unprocessed class definitions without inheritance"""
        raw_classes: Dict[str, RawClassDef] = {}
        
        pbo_prefix = self._get_pbo_prefix(code_files)
        
        for file_path, content in code_files.items():
            if self._progress_callback:
                self._progress_callback(file_path)
            try:
                # Just collect raw definitions without processing inheritance
                class_defs = self.parser.parse_class_definitions(content, pbo_prefix)
                for name, info in class_defs.items():
                    self._add_or_update_class(raw_classes, name, info, file_path, source)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                
        # Return unprocessed classes - inheritance will be handled later
        return UnprocessedClasses(classes=raw_classes, source=source)

    def build_class_hierarchy(self, unprocessed: UnprocessedClasses) -> ClassHierarchy:
        """Build class hierarchy after all classes have been collected"""
        all_classes: Dict[str, ClassInfo] = {}
        invalid_classes: Set[str] = set()
        
        # Convert raw definitions to ClassInfo objects
        for name, raw_def in unprocessed.classes.items():
            all_classes[name] = ClassInfo(
                name=name,
                parent=raw_def.parent,
                properties=raw_def.properties,
                file_path=raw_def.file_path,
                source=raw_def.source,
                type=raw_def.type
            )

        # Now process inheritance for all classes at once
        processed_classes, root_classes, invalid = self._process_inheritance(all_classes)
        
        return ClassHierarchy(
            classes=processed_classes,
            root_classes=root_classes,
            source=unprocessed.source,
            invalid_classes=invalid
        )

    def _process_inheritance(self, classes: Dict[str, ClassInfo]) -> Tuple[Dict[str, ClassInfo], Set[str], Set[str]]:
        """Process inheritance relationships after all classes are collected"""
        processed_classes: Dict[str, ClassInfo] = {}
        root_classes: Set[str] = set()
        invalid_classes: Set[str] = set()

        # First detect inheritance cycles
        for name in classes:
            self._detect_inheritance_cycle(name, set(), classes, invalid_classes)

        # Process valid classes
        for name, info in classes.items():
            if name in invalid_classes:
                continue

            inheritance_chain = self._build_inheritance_chain(name, classes)
            if not inheritance_chain:
                continue

            # Calculate inherited properties through the chain
            inherited_props = {}
            for ancestor in inheritance_chain[:-1]:  # Exclude the class itself
                if ancestor in classes:
                    inherited_props.update(classes[ancestor].properties)

            # Find direct children
            children = {
                c for c, i in classes.items()
                if i.parent == name and c not in invalid_classes
            }

            processed_classes[name] = ClassInfo(
                name=name,
                parent=info.parent,
                properties=info.properties,
                inherited_properties=inherited_props,
                file_path=info.file_path,
                source=info.source,
                children=children,
                type=info.type
            )

            if not info.parent:
                root_classes.add(name)

        return processed_classes, root_classes, invalid_classes

    def _add_or_update_class(self, raw_classes: Dict[str, RawClassDef], 
                           name: str, info: Dict, file_path: str, source: str) -> None:
        """Add or update class definition"""
        new_def = RawClassDef(
            name=name,
            parent=info['parent'],
            properties=info['properties'],
            file_path=Path(file_path),
            source=source,
            type=info.get('type', 'class')
        )
        
        if name in raw_classes:
            if len(info['properties']) > len(raw_classes[name].properties):
                raw_classes[name] = new_def
        else:
            raw_classes[name] = new_def

    def read_pbo_code(self, pbo_path: Path) -> Dict[str, str]:
        """Read code files from PBO using extractor
        
        Args:
            pbo_path: Path to PBO file
            
        Returns:
            Dictionary of relative paths to file contents
        """
        if self._progress_callback:
            self._progress_callback(str(pbo_path))
        if not pbo_path.is_file():
            logger.error(f"PBO file not found: {pbo_path}")
            return {}
            
        return self.pbo_extractor.extract_code_files(pbo_path)

    def find_code_references(self, search_term: str, code: str) -> List[tuple]:
        """Find references to a term in code content"""
        references = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if search_term in line:
                references.append((line_num, line.strip()))
                
        return references

    def read_code_file(self, file_path: Path) -> Optional[str]:
        """Read a code file with proper encoding detection"""
        try:
            # Try UTF-8 first
            return file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # Fallback to Windows-1252
                return file_path.read_text(encoding='windows-1252')
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                return None

    def _get_pbo_prefix(self, code_files: Dict[str, str]) -> Optional[str]:
        """Extract PBO prefix from config files"""
        for file_path, content in code_files.items():
            if 'config.' in file_path.lower():
                prefix_match = re.search(r'^\s*prefix\s*=\s*"([^"]+)"\s*;', 
                                      content, re.MULTILINE)
                if prefix_match:
                    return prefix_match.group(1).replace('\\', '/')
        return None
