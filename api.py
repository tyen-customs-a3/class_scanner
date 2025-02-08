from pathlib import Path
from typing import Dict, Callable, Optional

from src.models import ClassData, PboClasses



class Scanner:
    def scan_pbo(self, path: Path) -> Optional[PboClasses]:
        """Basic implementation for testing"""
        if not path.exists():
            return None

        # Return minimal valid data for testing
        return PboClasses(
            classes={
                "TestClass": ClassData(
                    name="TestClass",
                    parent="Object",
                    properties={},
                    source_file=Path("config.cpp")
                )
            },
            source=str(path)
        )


class API:
    def __init__(self):
        self.scanner = Scanner()
        self._cache = {}
        self._progress_callback = None

    def set_progress_callback(self, callback: Callable[[str], None]):
        self._progress_callback = callback

    def clear_cache(self):
        self._cache.clear()

    def scan_directory(self, directory: Path, file_limit: Optional[int] = None) -> Dict[str, PboClasses]:
        results = {}
        pbo_files = list(directory.glob("*.pbo"))

        if file_limit:
            pbo_files = pbo_files[:file_limit]

        for pbo_path in pbo_files:
            str_path = str(pbo_path)

            if str_path in self._cache:
                results[str_path] = self._cache[str_path]
                continue

            if self._progress_callback:
                self._progress_callback(str_path)

            scan_result = self.scanner.scan_pbo(pbo_path)
            if scan_result:
                self._cache[str_path] = scan_result
                results[str_path] = scan_result

        return results
