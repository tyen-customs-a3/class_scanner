from pathlib import Path
import logging
from typing import Dict
from class_scanner import ClassAPI, ClassHierarchy

def scan_game_folders(api: ClassAPI, game_path: Path, mods_path: Path, logger: logging.Logger) -> Dict[str, ClassHierarchy]:
    """Scan both game and mod directories for class definitions"""
    results = {}
    
    # Scan main game directory
    if game_path.exists():
        logger.info(f"Scanning game directory: {game_path}")
        addons_path = game_path / "Addons"
        if addons_path.exists():
            result = api.scan_directory(addons_path)
            if result.success:
                results.update(result.hierarchies)
                logger.info(f"Found {len(result.hierarchies)} class hierarchies in game directory")
    
    # Scan mods directory
    if mods_path.exists():
        logger.info(f"Scanning mods directory: {mods_path}")
        for mod_dir in mods_path.iterdir():
            if mod_dir.is_dir():
                addons_path = mod_dir / "addons"
                if addons_path.exists():
                    result = api.scan_directory(addons_path)
                    if result.success:
                        results.update(result.hierarchies)
                        logger.info(f"Found {len(result.hierarchies)} class hierarchies in {mod_dir.name}")
    
    return results
