import logging
from pathlib import Path
from typing import Dict, Optional, cast, Callable, Union, List

from class_scanner.constants import ConfigSectionName, CFG_GLOBAL
from class_scanner.models import ClassData, PboScanData
from class_scanner.parser.class_parser import ClassParser
from class_scanner.pbo.pbo_extractor import PboExtractor
logger = logging.getLogger(__name__)


class Scanner:
    """Scanner class for PBO scanning operations"""
    
    def __init__(self):
        self.parser = ClassParser()
        self.extractor = PboExtractor()

    def scan_directory(self, directory: Union[str, Path]) -> Dict[str, PboScanData]:
        """Scan a directory for PBO files and their class definitions"""
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            logger.debug(f"Directory does not exist or is not a directory: {directory}")
            return {}

        results: Dict[str, PboScanData] = {}
        for pbo_file in directory.rglob('*.pbo'):
            if result := self.scan_pbo(pbo_file):
                results[str(pbo_file)] = result

        return results

    def scan_pbo(self, path: Path) -> Optional[PboScanData]:
        """Scan a PBO file for class definitions"""
        try:
            code_files = self.extractor.extract_code_files(path)
            if not code_files:
                logger.debug(f"No code files found in {path}")
                return None

            config_content = next(
                (content for name, content in code_files.items() 
                 if name.lower().endswith('config.cpp')),
                None
            )
            
            if not config_content:
                logger.debug(f"No config.cpp found in {path}")
                return None

            sections = self.parser.parse_class_definitions(config_content)
            
            classes = {}
            for section_name, section_classes in sections.items():
                for class_name, class_info in section_classes.items():
                    classes[class_name] = ClassData(
                        name=class_name,
                        parent=class_info.get('parent', ''),
                        properties=class_info.get('properties', {}),
                        source_file=path,
                        container=section_name,
                        config_type=section_name
                    )

            # Always return a PboClasses object even if empty
            return PboScanData(
                classes=classes,
                source=path.stem
            )

        except Exception as e:
            logger.error(f"Error scanning PBO {path}: {e}", exc_info=True)
            return None
