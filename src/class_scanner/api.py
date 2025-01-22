import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from .models import (
    ClassHierarchy, UnprocessedClasses,
    ScanResult, ValidationResult, BatchValidationResult
)
from .scanner import ClassScanner
from .pbo_extractor import PboExtractor
from .cache import ClassCacheManager, CacheConfig

logger = logging.getLogger(__name__)

@dataclass
class ClassAPIConfig:
    """Configuration for ClassAPI"""
    cache_config: Optional[CacheConfig] = field(default_factory=lambda: CacheConfig())
    scan_timeout: int = 30
    max_pbo_size: int = 100_000_000
    parallel_scan: bool = True
    max_workers: int = 4
    cache_max_age: int = 3600

    def __post_init__(self):
        if self.cache_config and self.cache_max_age != 3600:
            self.cache_config = CacheConfig(max_age=self.cache_max_age)

class ClassAPI:
    """Simplified API focusing on high-level operations"""
    
    API_VERSION = "1.0"
    
    def __init__(self, config: Optional[ClassAPIConfig] = None):
        """Initialize API with optional configuration"""
        self.config = config or ClassAPIConfig()
        self._scanner = ClassScanner()
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        self._logger = logging.getLogger(__name__)
        self._cache = ClassCacheManager(self.config.cache_config)
        self._progress_callback = None

    def cleanup(self):
        """Clean up resources"""
        if self._executor:
            self._executor.shutdown(wait=True)
        self._scanner.pbo_extractor.cleanup()

    def scan_game(self, game_path: Path) -> ScanResult:
        """Scan game directory"""
        return self.scan_directory(game_path / "Addons")

    def scan_mod(self, mod_path: Path) -> ScanResult:
        """Scan mod directory"""
        return self.scan_directory(mod_path / "addons")

    def validate_mod(self, mod_path: Path) -> ValidationResult:
        """Validate mod against cached game classes"""
        scan_result = self.scan_mod(mod_path)
        issues = {}
        
        for addon_name, hierarchy in scan_result.hierarchies.items():
            addon_issues = []
            for class_name, info in hierarchy.classes.items():
                if info.parent and not self._cache.validate_class(info.parent):
                    addon_issues.append(
                        f"Class '{class_name}' inherits from unknown class '{info.parent}'"
                    )
                    similar = self._cache.find_similar_classes(info.parent)
                    if similar:
                        addon_issues.append(f"Did you mean one of: {', '.join(similar)}?")
            
            if addon_issues:
                issues[addon_name] = addon_issues
                
        return ValidationResult(
            valid=not bool(issues),
            issues=issues,
            addon_name=str(mod_path)
        )

    def scan_pbo(self, file_path: Path) -> Optional[ClassHierarchy]:
        """Scan a PBO file or direct code file"""
        if file_path.suffix.lower() == '.pbo':
            try:
                if not file_path.exists():
                    self._logger.error(f"PBO file not found: {file_path}")
                    return None
                    
                # Check cache first
                if self._cache.is_valid():
                    cached = self._cache.get_hierarchy(str(file_path))
                    if cached:
                        return cached
                        
                code_files = self._scanner.read_pbo_code(file_path)
                if not code_files:
                    return None
                    
                raw_classes = self._scanner.scan_classes(str(file_path), code_files)
                if not raw_classes or not raw_classes.classes:
                    return None
                    
                hierarchy = raw_classes.build_hierarchy()
                self._cache.add_hierarchy(str(file_path), hierarchy)
                return hierarchy
                
            except Exception as e:
                self._logger.error(f"Error scanning PBO {file_path}: {e}")
                return None
        else:
            return self.scan_file(file_path)

    def clear_cache(self) -> None:
        """Clear the cache"""
        self._cache.clear()

    def scan_file(self, file_path: Path) -> Optional[ClassHierarchy]:
        """Scan a non-PBO file directly"""
        try:
            if not file_path.exists():
                self._logger.error(f"File not found: {file_path}")
                return None

            # Check cache first
            if self._cache.is_valid():
                cached = self._cache.get_hierarchy(str(file_path))
                if cached:
                    return cached

            # Read file with multiple encodings
            code_content = None
            for encoding in ['utf-8-sig', 'utf-8', 'windows-1252', 'latin1']:
                try:
                    code_content = file_path.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if code_content is None:
                self._logger.error(f"Failed to read file with supported encodings: {file_path}")
                return None

            raw_classes = self._scanner.scan_classes(str(file_path), {str(file_path): code_content})
            
            if not raw_classes or not raw_classes.classes:
                return None

            hierarchy = raw_classes.build_hierarchy()
            self._cache.add_hierarchy(str(file_path), hierarchy)
            return hierarchy

        except Exception as e:
            self._logger.error(f"Error scanning file {file_path}: {e}")
            return None

    def find_class(self, class_name: str) -> Dict[str, ClassHierarchy]:
        """Find class definitions across all cached hierarchies"""
        results = {}
        for source, hierarchy in self._cache.get_all_hierarchies().items():
            if class_name in hierarchy.classes:
                results[source] = hierarchy
        return results

    def find_classes_with_parent(self, parent_name: str) -> Dict[str, Set[str]]:
        """Find all classes inheriting from given parent"""
        return self._cache.find_classes_with_parent(parent_name)

    def find_classes_with_property(self, property_name: str) -> Dict[str, Set[str]]:
        """Find all classes that have a specific property"""
        return self._cache.find_classes_with_property(property_name)

    def get_cached_hierarchy(self, source: str) -> Optional[ClassHierarchy]:
        """Get a class hierarchy from cache by source
        
        Args:
            source: Source identifier (usually file path)
            
        Returns:
            Cached ClassHierarchy if found and valid, None otherwise
        """
        if not self._cache.is_valid():
            return None
        return self._cache.get_hierarchy(source)

    def scan_directory(self, directory: Path, file_limit: Optional[int] = None) -> ScanResult:
        """Recursively scan a directory for PBO files and process them"""
        if not directory.exists():
            return ScanResult.error(directory, "Directory does not exist")
            
        hierarchies = {}
        errors = {}
        skipped = set()
        
        # Find all PBO files first and convert to strings to avoid Path serialization issues
        pbo_files = [(str(p), p) for p in directory.rglob("*.pbo")]
        if file_limit is not None:
            pbo_files = pbo_files[:file_limit]
        total_files = len(pbo_files)
        
        if self.config.parallel_scan and total_files > 1:
            # Process PBOs in parallel using thread pool
            completed = 0
            active_futures = []
            
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                # Submit initial batch
                batch_size = min(50, total_files)
                while completed < total_files:
                    # Calculate how many new tasks to submit
                    remaining = total_files - completed
                    current_batch = min(batch_size, remaining)
                    
                    # Submit new batch
                    for pbo_str, pbo_path in pbo_files[completed:completed + current_batch]:
                        future = executor.submit(self.scan_pbo, pbo_path)
                        active_futures.append((pbo_str, future))
                    
                    # Wait for and process completed futures
                    for pbo_str, future in active_futures:
                        try:
                            hierarchy = future.result(timeout=self.config.scan_timeout)
                            if hierarchy and hierarchy.classes:
                                hierarchies[pbo_str] = hierarchy
                            else:
                                skipped.add(pbo_str)
                        except Exception as e:
                            logger.error(f"Error processing {pbo_str}: {e}")
                            errors[pbo_str] = str(e)
                    
                    # Clear processed futures
                    active_futures.clear()
                    completed += current_batch
                    
                    if self._progress_callback:
                        self._progress_callback(f"Processed {completed}/{total_files} files")
        else:
            # Process PBOs sequentially for small sets
            for pbo_str, pbo_path in pbo_files:
                try:
                    if hierarchy := self.scan_pbo(pbo_path):
                        hierarchies[pbo_str] = hierarchy
                    else:
                        skipped.add(pbo_str)
                except Exception as e:
                    logger.error(f"Error processing {pbo_str}: {e}")
                    errors[pbo_str] = str(e)
                if self._progress_callback:
                    self._progress_callback(str(pbo_path))
                
        return ScanResult.from_scan(hierarchies, errors, skipped)

    def get_cached_hierarchies(self) -> Dict[str, ClassHierarchy]:
        """Get all cached hierarchies"""
        return self._cache.get_all_hierarchies()

    def set_progress_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """Set a callback function to track scanning progress
        
        Args:
            callback: Function that takes a single string parameter (file path)
        """
        self._progress_callback = callback
        self._scanner.set_progress_callback(callback)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
