import logging
from pathlib import Path
from typing import Dict, Optional, cast, Callable, Union, List

from class_scanner.parser.class_parser import ClassParser
from class_scanner.pbo.pbo_extractor import PboExtractor
from class_scanner.models import ClassData, PboClasses
from class_scanner.constants import ConfigSectionName, CFG_GLOBAL

logger = logging.getLogger(__name__)


class ClassScanner:
    """Simplified class scanner that only extracts basic class data"""

    def __init__(self) -> None:
        self.extractor = PboExtractor()
        self.parser = ClassParser()
        self.progress_callback: Optional[Callable[[Union[str, Path]], None]] = None

    def scan_directory(self, directory: Union[str, Path]) -> Dict[str, PboClasses]:
        """Scan a directory for PBO files and extract classes"""
        directory = Path(directory)
        results = {}

        for pbo_path in directory.rglob('*.pbo'):
            try:
                pbo_result = self.scan_pbo(pbo_path)
                if pbo_result and pbo_result.classes:
                    results[str(pbo_path)] = pbo_result
                if self.progress_callback:
                    self.progress_callback(str(pbo_path))
            except Exception as e:
                logger.error(f"Failed to scan {pbo_path}: {e}")

        return results

    def scan_pbo(self, pbo_path: Path) -> Optional[PboClasses]:
        """Extract and parse classes from a single PBO file"""
        try:
            code_files = self.extractor.extract_code_files(pbo_path)
            all_classes: Dict[str, ClassData] = {}

            for filepath, content in code_files.items():
                if not filepath.lower().endswith(('.cpp', '.hpp')):
                    continue

                class_defs = self.parser.parse_class_definitions(content)
                
                # Add top-level section classes first
                for section_name, section in cast(Dict[ConfigSectionName, Dict], class_defs).items():
                    if section_name != CFG_GLOBAL:
                        # Add the section itself as a class
                        all_classes[section_name] = ClassData(
                            name=section_name,
                            parent='',
                            properties={},
                            source_file=Path(filepath)
                        )
                        
                        # Process classes in the section
                        for name, data in section.items():
                            clean_name = self._clean_class_name(str(name))
                            if clean_name:
                                all_classes[clean_name] = ClassData(
                                    name=clean_name,
                                    parent=self._clean_class_name(str(data.get('parent', ''))),
                                    properties=data.get('properties', {}),
                                    source_file=Path(filepath)
                                )
                
                # Process global classes
                for name, data in class_defs[CFG_GLOBAL].items():
                    clean_name = self._clean_class_name(str(name))
                    if clean_name:
                        all_classes[clean_name] = ClassData(
                            name=clean_name,
                            parent=self._clean_class_name(str(data.get('parent', ''))),
                            properties=data.get('properties', {}),
                            source_file=Path(filepath)
                        )

            if all_classes:
                return PboClasses(classes=all_classes, source=str(pbo_path))

        except Exception as e:
            logger.error(f"Error processing {pbo_path}: {e}")
            logger.debug("Exception details:", exc_info=True)

        return None

    def _clean_class_name(self, name: str) -> str:
        """Clean class name of any artifacts"""
        if not name:
            return ''
        return name.rstrip('{;}').strip()

from pathlib import Path
from typing import Optional
from .models.core import PboClasses

class Scanner:
    def __init__(self):
        pass

    def scan_pbo(self, path: Path) -> Optional[PboClasses]:
        """Scan a PBO file for class definitions"""
        # TODO: Implement actual scanning logic
        return None
