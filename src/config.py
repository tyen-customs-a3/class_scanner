from dataclasses import dataclass
from pathlib import Path
from typing import Optional, FrozenSet  # Changed from Set

@dataclass(frozen=True)
class ScannerSettings:
    temp_dir: Path = Path('temp')
    max_file_size: int = 100_000_000  # 100MB
    allowed_extensions: FrozenSet[str] = frozenset({'.cpp', '.hpp', '.h', '.bin'})
    timeout: int = 30
    debug: bool = False
    cache_enabled: bool = True
    cache_dir: Optional[Path] = None

class Config:
    def __init__(self):
        self._settings = ScannerSettings()
    
    @property
    def settings(self) -> ScannerSettings:
        return self._settings

    def update_settings(self, **kwargs) -> ScannerSettings:
        self._settings = ScannerSettings(**{
            **self._settings.__dict__,
            **kwargs
        })
        return self._settings

# Global config instance
config = Config()
