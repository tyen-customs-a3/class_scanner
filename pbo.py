import logging
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager


class PboProcessor:
    def __init__(self, config):
        self.config = config
        self._temp_dir = Path('temp')

    @contextmanager
    def _temp_extraction(self, pbo_path: Path):
        """Context manager for temporary PBO extraction"""
        try:
            yield self._temp_dir
        finally:
            pass

    def extract_configs(self, pbo_path: Path) -> Iterator[Path]:
        """Extract and yield paths to config files"""
        try:
            with self._temp_extraction(pbo_path) as temp_dir:
                for file in temp_dir.rglob('*.cpp'):
                    yield file
        except Exception as e:
            logging.error(f"Failed to process {pbo_path}: {e}")
