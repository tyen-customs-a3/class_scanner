import sys
import logging
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import argparse
from typing import Dict
import tempfile
import shutil

from class_scanner.models.base import ClassHierarchy
from utils import ensure_temp_dir, setup_python_path
from scanning import scan_game_folders
from reporting import generate_class_report
from class_scanner import ClassAPI, ClassAPIConfig

DEFAULT_ARMA3_PATH = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Arma 3")
DEFAULT_MODS_PATH = Path(r"C:\pca")
PROJECT_ROOT = Path(__file__).parent.parent

def scan_game_folders(api: ClassAPI, game_path: Path, mods_path: Path, logger: logging.Logger, file_limit: int = None, skip_base: bool = False) -> Dict[str, ClassHierarchy]:
    """Scan both game and mod directories for class definitions"""
    results = {}
    files_processed = 0
    total_processed = {'game': 0, 'mods': 0}

    # Scan game directory if not skipped
    if not skip_base and game_path.exists() and (file_limit is None or files_processed < file_limit):
        addons_path = game_path / "Addons"
        if addons_path.exists():
            remaining = None if file_limit is None else file_limit - files_processed
            scan_result = api.scan_directory(addons_path, file_limit=remaining)
            if scan_result.success:
                results.update(scan_result.hierarchies)
                files_processed += len(scan_result.hierarchies)
                total_processed['game'] = len(scan_result.hierarchies)

    # Scan mods directory if limit not reached
    if mods_path.exists() and (file_limit is None or files_processed < file_limit):
        for mod_dir in mods_path.iterdir():
            if file_limit is not None and files_processed >= file_limit:
                break
                
            if mod_dir.is_dir():
                addons_path = mod_dir / "addons"
                if addons_path.exists():
                    remaining = None if file_limit is None else file_limit - files_processed
                    scan_result = api.scan_directory(addons_path, file_limit=remaining)
                    if scan_result.success:
                        results.update(scan_result.hierarchies)
                        files_processed += len(scan_result.hierarchies)
                        total_processed['mods'] += len(scan_result.hierarchies)

    return results

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scan Arma 3 and mods for class definitions')
    parser.add_argument('--game', type=Path, help='Path to Arma 3 directory')
    parser.add_argument('--mods', type=Path, help='Path to Arma 3 mods directory')
    parser.add_argument('--limit', type=int, help='Limit number of files to scan')
    parser.add_argument('--verbose', action='store_true', help='Show detailed progress')
    parser.add_argument('--skip-base', action='store_true', help='Skip scanning base game files')
    args = parser.parse_args()

    # Find game and mods directories if not specified
    game_path = args.game or DEFAULT_ARMA3_PATH
    mods_path = args.mods or DEFAULT_MODS_PATH

    # Setup directories and logging
    setup_python_path(Path(__file__))
    temp_dir = ensure_temp_dir(PROJECT_ROOT)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = temp_dir / f"scan_{timestamp}.log"

    # Setup logging - only file handler by default
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler gets everything
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Console handler only gets critical messages unless verbose
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    console_handler.setLevel(logging.DEBUG if args.verbose else logging.CRITICAL)
    logger.addHandler(console_handler)

    try:
        # Initialize API with configuration
        config = ClassAPIConfig(
            cache_max_age=3600,
            scan_timeout=120
        )
        api = ClassAPI(config)
        
        # Create progress bar with fixed width description
        BAR_WIDTH = 20  # Total width of progress bar
        DESC_WIDTH = 50  # Fixed width for description text
        
        with tqdm(desc="Scanning files".ljust(DESC_WIDTH), unit="", ncols=BAR_WIDTH, disable=args.verbose) as pbar:
            scanned_files = 0
            
            def progress_callback(status: str):
                nonlocal scanned_files
                if isinstance(status, str):
                    if status.startswith("Processed"):
                        # Update for batch completion
                        current, total = map(int, status.split()[1].split('/'))
                        pbar.update(current - scanned_files)
                        scanned_files = current
                    else:
                        # Update for single file with fixed width description
                        pbar.update(1)
                        scanned_files += 1
                        if not status.startswith("Processed"):
                            filename = Path(status).name
                            desc = f"Scanning {filename}"
                            # Truncate or pad to fixed width
                            desc = desc[:DESC_WIDTH].ljust(DESC_WIDTH)
                            pbar.set_description(desc)
            
            api.set_progress_callback(progress_callback)
            results = scan_game_folders(api, game_path, mods_path, logger, args.limit, args.skip_base)
            
            # Final status with fixed width
            total_classes = sum(len(h.classes) for h in results.values())
            final_desc = f"Completed: {scanned_files} files".ljust(DESC_WIDTH)
            pbar.set_description(final_desc)

        logger.critical(f"Found {total_classes} classes in {scanned_files} files")
        
        # Generate and save report
        report_dir = temp_dir / f"{timestamp}"
        generate_class_report(api, results, report_dir)
        logger.critical(f"Report written to: {report_dir}")
        
    except KeyboardInterrupt:
        logger.critical("\nScan interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"\nError during scan: {e}")
        sys.exit(1)
    finally:
        api.clear_cache()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

if __name__ == "__main__":
    main()
