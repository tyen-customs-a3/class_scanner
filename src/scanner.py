import logging
from pathlib import Path
from typing import Dict, Optional
from .parser import ClassParser
from .models import ClassData, PboClasses
from .pbo_extractor import PboExtractor

logger = logging.getLogger(__name__)


class ClassScanner:
    """Simplified class scanner that only extracts basic class data"""

    def __init__(self):
        self.extractor = PboExtractor()
        self.parser = ClassParser()

    def scan_directory(self, directory: Path) -> Dict[str, PboClasses]:
        """Scan a directory for PBO files and extract classes"""
        results = {}

        for pbo_path in directory.rglob('*.pbo'):
            try:
                pbo_result = self.scan_pbo(pbo_path)
                if pbo_result and pbo_result.classes:
                    results[str(pbo_path)] = pbo_result
            except Exception as e:
                logger.error(f"Failed to scan {pbo_path}: {e}")

        return results

    def scan_pbo(self, pbo_path: Path) -> Optional[PboClasses]:
        """Extract and parse classes from a single PBO file"""
        try:
            code_files = self.extractor.extract_code_files(pbo_path)
            all_classes = {}

            for filepath, content in code_files.items():
                if not filepath.lower().endswith(('.cpp', '.hpp')):
                    continue

                class_defs = self.parser.parse_class_definitions(content)
                for section_name, section in class_defs.items():
                    for name, data in section.items():
                        if not name:
                            continue

                        clean_name = name.rstrip('{;}') if isinstance(name, str) else name
                        if clean_name.endswith('{}'):
                            clean_name = clean_name[:-2]

                        parent = data.get('parent', '')
                        clean_parent = parent.rstrip('{;}') if isinstance(parent, str) else ''
                        if clean_parent.endswith('{}'):
                            clean_parent = clean_parent[:-2]

                        if clean_name:
                            all_classes[clean_name] = ClassData(
                                name=clean_name,
                                parent=clean_parent,
                                properties=data.get('properties', {}),
                                source_file=Path(filepath)
                            )

            if all_classes:
                return PboClasses(
                    classes=all_classes,
                    source=str(pbo_path)
                )

        except Exception as e:
            logger.error(f"Error processing {pbo_path}: {e}")
            logger.debug("Exception details:", exc_info=True)

        return None
