from pathlib import Path
from typing import Dict, Callable, Optional, Any
import logging
import struct
import io
import logging
from pathlib import Path
from typing import Dict, Optional, Callable, Union
from class_scanner.models import ClassData, PboClasses, PropertyValue
from class_scanner.parser.class_parser import ClassParser
from class_scanner.scanner import Scanner

logger = logging.getLogger(__name__)

class ClassScanner:
    def __init__(self):
        self.parser = ClassParser()

    def scan_pbo(self, path: Path) -> Optional[PboClasses]:
        """Scan a PBO file and extract class definitions"""
        try:
            if not path.exists() or not path.is_file():
                logger.debug(f"Invalid file path: {path}")
                return None

            with open(path, 'rb') as f:
                # Validate PBO header
                header = f.read(8)
                if not header.startswith(b'\0sreV'):
                    logger.debug(f"Invalid PBO header in {path}")
                    return None

                # Read PBO content
                content = self._extract_config_cpp(f)
                if not content:
                    logger.debug(f"No config.cpp found in {path}")
                    return None

                # Parse class definitions
                config_sections = self.parser.parse_class_definitions(content)
                
                # Convert parsed sections to ClassData objects with proper section handling
                classes = {}
                for section_name, section_classes in config_sections.items():
                    for class_name, class_info in section_classes.items():
                        classes[class_name] = ClassData(
                            name=class_name,
                            parent=class_info['parent'],
                            properties=class_info['properties'],
                            source_file=path,
                            container=section_name,
                            config_type=section_name if section_name != 'CfgGlobal' else ''
                        )

                        # Handle inheritance chain
                        parent_name = class_info['parent']
                        if parent_name and parent_name not in classes:
                            # Add placeholder parent class if not already present
                            classes[parent_name] = ClassData(
                                name=parent_name,
                                parent='',
                                properties={},
                                source_file=path,
                                container=section_name
                            )

                return PboClasses(
                    classes=classes,
                    source=path.parent.name
                )

        except Exception as e:
            logger.debug(f"Error scanning PBO {path}: {e}", exc_info=True)
            return None

    def _extract_config_cpp(self, file: io.BufferedReader) -> Optional[str]:
        """Extract config.cpp content from PBO file"""
        try:
            # Skip remaining header entries
            while True:
                filename = b''
                char = file.read(1)
                while char and char != b'\0':
                    filename += char
                    char = file.read(1)
                
                if not filename:
                    break
                    
                # Skip properties
                file.seek(16, 1)  # Skip 4 integers (4 bytes each)

            # Search for config.cpp in file entries
            while True:
                filename = b''
                char = file.read(1)
                while char and char != b'\0':
                    filename += char
                    char = file.read(1)
                
                if not filename:
                    break

                if filename.lower() == b'config.cpp':
                    # Read file properties
                    packing, timestamp, size = struct.unpack('III', file.read(12))
                    file.seek(4, 1)  # Skip one more integer
                    
                    # Read file content
                    content = file.read(size)
                    if packing == 0:  # Uncompressed
                        return content.decode('utf-8', errors='ignore')
                    else:
                        logger.debug("Compressed config.cpp not supported yet")
                        return None
                else:
                    # Skip this entry
                    file.seek(16, 1)

            return None

        except Exception as e:
            logger.debug("Error extracting config.cpp: %s", e)
            return None

class ClassAPI:
    """Main API class for class scanning functionality"""
    
    def __init__(self) -> None:
        """Initialize API with default configuration"""
        self.scanner = Scanner()
        self._cache: Dict[str, PboClasses] = {}
        self._progress_callback: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for progress updates"""
        self._progress_callback = callback

    def clear_cache(self) -> None:
        """Clear the results cache"""
        self._cache.clear()

    def scan_directory(self, directory: Union[str, Path], file_limit: Optional[int] = None) -> Dict[str, PboClasses]:
        """Scan a directory for PBO files and their classes"""
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            return {}

        results: Dict[str, PboClasses] = {}
        processed = 0

        pbo_files = list(directory.rglob('*.pbo'))
        if file_limit:
            pbo_files = pbo_files[:file_limit]

        for pbo_file in pbo_files:
            if self._progress_callback:
                self._progress_callback(f"Processing {pbo_file}")

            if result := self.scan_pbo(pbo_file):
                results[str(pbo_file)] = result
                processed += 1

        return results

    def scan_pbo(self, pbo_path: Union[str, Path]) -> Optional[PboClasses]:
        """Scan a single PBO file for class definitions"""
        pbo_path = Path(pbo_path)
        if not pbo_path.exists():
            logger.debug("Invalid file path: %s", pbo_path)
            return None

        cache_key = str(pbo_path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if result := self.scanner.scan_pbo(pbo_path):
            self._cache[cache_key] = result
            return result

        return None
