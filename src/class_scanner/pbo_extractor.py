import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, Set, Tuple
import shutil
import tempfile
import uuid

logger = logging.getLogger(__name__)

class PboExtractor:
    """Helper class for PBO file operations using extractpbo tool"""
    
    # Update BIN_FILE_TYPES to include txt files
    BIN_FILE_TYPES = {
        'config.bin': 'config.cpp',
        'model.bin': 'model.cfg',
        'stringtable.bin': 'stringtable.xml',
        'texheaders.bin': 'texheaders.txt',  # Changed from .h to .txt
        'script.bin': 'script.cpp',
        'default': '.txt'  # Default to .txt for unknown bin files
    }
    
    # Update CODE_EXTENSIONS to include txt files
    CODE_EXTENSIONS = {'.cpp', '.hpp', '.h', '.txt'}
    
    def __init__(self, timeout: int = 30):
        """Initialize PBO extractor with timeout
        
        Args:
            timeout: Maximum time in seconds to wait for extractpbo operations
        """
        self.timeout = timeout
        self._temp_base = Path(tempfile.gettempdir()) / "pbo_extractor"
        self._temp_dirs = set()  # Track all created temp directories

    def __del__(self):
        """Cleanup temporary resources"""
        self.cleanup()

    def cleanup(self):
        """Remove all temporary directories"""
        for temp_dir in self._temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
        self._temp_dirs.clear()

    def _create_temp_dir(self) -> Path:
        """Create a unique temporary directory for extraction"""
        # Create base temp directory if it doesn't exist
        self._temp_base.mkdir(parents=True, exist_ok=True)
        
        # Create unique subdirectory using UUID
        temp_dir = self._temp_base / f"extract_{uuid.uuid4().hex}"
        temp_dir.mkdir(parents=True)
        self._temp_dirs.add(temp_dir)
        return temp_dir

    def list_contents(self, pbo_path: Path) -> Tuple[int, str, str]:
        """List contents of PBO file
        
        Args:
            pbo_path: Path to PBO file
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        result = subprocess.run(
            ['extractpbo', '-LBP', str(pbo_path)],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        return result.returncode, result.stdout, result.stderr

    def _detect_bin_type(self, file_path: str) -> Optional[str]:
        """Detect the type of a .bin file and return appropriate extension"""
        basename = Path(file_path).name.lower()
        return self.BIN_FILE_TYPES.get(basename) or (
            basename.rsplit('.', 1)[0] + self.BIN_FILE_TYPES['default']
            if basename.endswith('.bin') else None
        )

    def extract_files(self, pbo_path: Path, output_dir: Path, file_filter: Optional[str] = None) -> Tuple[int, str, str]:
        """Extract files from PBO with bin file handling"""
        cmd = ['extractpbo', '-S', '-P', '-Y']
        if file_filter:
            # Fix: -F requires equals sign syntax
            cmd.append(f'-F={file_filter}')
        cmd.extend([str(pbo_path), str(output_dir)])
        
        logger.debug(f"Running extractpbo command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Handle bin file renaming after extraction
        if result.returncode == 0:
            self._process_extracted_bins(output_dir)
            
        return result.returncode, result.stdout, result.stderr

    def _process_extracted_bins(self, output_dir: Path) -> None:
        """Process extracted bin files and rename them appropriately"""
        for bin_file in output_dir.rglob('*.bin'):
            try:
                if new_name := self._detect_bin_type(bin_file.name):
                    new_path = bin_file.with_name(new_name)
                    logger.debug(f"Renaming {bin_file.name} to {new_name}")
                    # Use replace() to handle existing files
                    bin_file.replace(new_path)
            except Exception as e:
                logger.warning(f"Failed to process bin file {bin_file}: {e}")

    def extract_prefix(self, stdout: str) -> Optional[str]:
        """Extract the prefix= line from extractpbo output
        
        Args:
            stdout: Output from extractpbo command
            
        Returns:
            Prefix string if found, None otherwise
        """
        for line in stdout.splitlines():
            if line.startswith('prefix='):
                # Always use forward slashes and strip semicolon
                prefix = line.split('=')[1].strip().strip(';')
                return prefix.replace('\\', '/')
        return None

    def extract_code_files(self, pbo_path: Path) -> Dict[str, str]:
        """Extract and read code files from PBO"""
        temp_dir = None
        try:
            temp_dir = self._create_temp_dir()
            logger.debug(f"Extracting PBO {pbo_path} to {temp_dir}")  # Changed to debug level
            
            # Extract files using extractpbo tool with options:
            # -P: don't pause
            # -S: silent
            # -Y: don't prompt for overwrites
            # -D: derapify files (convert binary to text)
            cmd = ['extractpbo', '-P', '-S', '-Y', '-D']
            
            # Prioritize .cpp files in filter
            extensions = ['.cpp'] + [ext for ext in self.CODE_EXTENSIONS if ext != '.cpp']
            extensions.append('.bin')
            extensions.append('.txt')
            extensions_filter = ','.join(f'*.{ext.lstrip(".")}' for ext in extensions)
            cmd.extend([f'-F={extensions_filter}'])
            
            # Add source and destination paths
            cmd.extend([str(pbo_path), str(temp_dir)])
            
            # Run extraction
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.warning(f"PBO extraction warning for {pbo_path}: {result.stderr}")
                # Continue anyway as partial extraction might have succeeded

            # Read extracted files
            code_files = {}
            
            # Look for all supported file types
            for ext in self.CODE_EXTENSIONS | {'.bin', '.txt'}:
                for file_path in temp_dir.rglob(f'*{ext}'):
                    try:
                        if file_path.suffix == '.bin':
                            if new_name := self._detect_bin_type(file_path.name):
                                file_path = file_path.with_name(new_name)
                        
                        if file_path.exists():
                            content = None
                            for encoding in ['utf-8-sig', 'utf-8', 'windows-1252', 'latin1']:
                                try:
                                    content = file_path.read_text(encoding=encoding)
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if content is not None:
                                relative_path = file_path.relative_to(temp_dir)
                                code_files[str(relative_path)] = content
                                logger.debug(f"Read file: {relative_path}")
                    except Exception as e:
                        if 'texheaders.txt' not in str(file_path):
                            logger.warning(f"Failed to read {file_path}: {e}")

            return code_files

        except Exception as e:
            logger.error(f"Error extracting code files from {pbo_path}: {e}")
            return {}
            
        finally:
            # Cleanup temp directory immediately after processing
            if temp_dir and temp_dir in self._temp_dirs:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    self._temp_dirs.remove(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
