import os
import sys
import json
from pathlib import Path
import tempfile
from datetime import datetime
from typing import Dict, Any, Set  # Added Set to imports
import logging
from tqdm import tqdm

# Add the src directory to Python path
src_path = str(Path(__file__).parent.parent / 'src')
if (src_path not in sys.path):
    sys.path.insert(0, src_path)

from class_scanner import ClassAPI, ClassAPIConfig, ClassHierarchy

DEFAULT_ARMA3_PATH = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Arma 3")
DEFAULT_MODS_PATH = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Arma 3\!Workshop")
PROJECT_ROOT = Path(__file__).parent.parent

def ensure_temp_dir() -> Path:
    """Create and return temp directory in project root"""
    temp_dir = PROJECT_ROOT / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def print_class_hierarchy(hierarchies: Dict[str, ClassHierarchy]) -> None:
    """Print a tree visualization of class hierarchies"""
    def build_tree(classes: Dict[str, Any], root_classes: Set[str], indent: str = "") -> None:
        # Sort root classes alphabetically
        for class_name in sorted(root_classes):
            info = classes.get(class_name)
            if not info:
                continue
                
            # Print current class with property count
            prop_count = len(info.properties)
            print(f"{indent}├── {class_name} ({prop_count} properties)")
            
            # Print important properties if they exist (sorted)
            important_props = {'scope', 'model', 'displayName', 'type', 'baseClass'}
            found_props = {k: v for k, v in sorted(info.properties.items()) if k in important_props}
            if found_props:
                for prop, value in sorted(found_props.items()):
                    print(f"{indent}│   ├── {prop} = {value}")
            
            # Sort children before recursing
            if info.children:
                build_tree(classes, sorted(info.children), indent + "│   ")

    # Group and sort hierarchies by source/addon
    print("\nClass Hierarchy by Source:")
    # Sort hierarchies by their source name
    for source, hierarchy in sorted(hierarchies.items(), key=lambda x: x[0].lower()):
        print(f"\n=== {Path(source).name} ===")
        # Build tree starting with sorted root classes
        build_tree(hierarchy.classes, hierarchy.root_classes)

def print_inheritance_tree(hierarchies: Dict[str, ClassHierarchy]) -> None:
    """Print complete inheritance tree of all classes"""
    # Build a complete inheritance map
    inheritance_map = {}
    reverse_map = {}  # child -> parent mapping
    all_classes = set()
    
    # First pass: collect all classes and their relationships
    for source, hierarchy in hierarchies.items():
        for class_name, info in hierarchy.classes.items():
            all_classes.add(class_name)
            if info.parent:
                if info.parent not in inheritance_map:
                    inheritance_map[info.parent] = set()
                inheritance_map[info.parent].add(class_name)
                reverse_map[class_name] = info.parent

    # Find root classes (no parent or parent not found)
    root_classes = {cls for cls in all_classes if cls not in reverse_map}

    def print_tree(class_name: str, indent: str = "", printed: Set[str] = None) -> None:
        if printed is None:
            printed = set()
            
        if class_name in printed:
            print(f"{indent}├── {class_name} (circular reference!)")
            return
            
        printed.add(class_name)
        children = inheritance_map.get(class_name, set())
        
        # Get class info from any hierarchy that contains this class
        class_info = None
        source_name = None
        for source, hierarchy in hierarchies.items():
            if class_name in hierarchy.classes:
                class_info = hierarchy.classes[class_name]
                source_name = Path(source).name
                break

        # Print current class with details
        if class_info:
            props_count = len(class_info.properties)
            print(f"{indent}├── {class_name} ({props_count} properties) [{source_name}]")
            
            # Print important properties
            important_props = {'scope', 'model', 'displayName', 'type', 'baseClass'}
            found_props = {k: v for k, v in sorted(class_info.properties.items()) if k in important_props}
            if found_props:
                for prop, value in sorted(found_props.items()):
                    print(f"{indent}│   ├── {prop} = {value}")
        else:
            print(f"{indent}├── {class_name} (reference only)")

        # Print children
        for child in sorted(children):
            print_tree(child, indent + "│   ", printed)

    # Print complete inheritance tree
    print("\nComplete Class Inheritance Tree:")
    print("Legend: ClassName (property count) [source PBO]")
    print("────────────────────────────────────────────")
    
    for root in sorted(root_classes):
        print_tree(root)
        print("────────────────────────────────────────────")

def print_addon_hierarchies(hierarchies: Dict[str, ClassHierarchy]) -> None:
    """Print class hierarchies grouped by addon folders"""
    # Group hierarchies by addon folder
    addon_groups = {}
    
    for source, hierarchy in hierarchies.items():
        path = Path(source)
        # Find addon root (starts with @)
        addon_root = None
        for parent in path.parents:
            if parent.name.startswith('@'):
                addon_root = parent.name
                break
        
        # Group by addon or 'Base Game' if no @ folder
        group_key = addon_root or 'Base Game'
        if group_key not in addon_groups:
            addon_groups[group_key] = {}
        addon_groups[group_key][source] = hierarchy

    # Print each addon's classes
    print("\nClasses by Addon:")
    print("=================")
    
    for addon_name, sources in sorted(addon_groups.items()):
        print(f"\n{addon_name}")
        print("─" * len(addon_name))
        
        # Collect all classes for this addon
        addon_classes = {}
        for source, hierarchy in sources.items():
            for class_name, info in hierarchy.classes.items():
                if class_name not in addon_classes:
                    addon_classes[class_name] = {
                        'source': Path(source).name,
                        'parent': info.parent,
                        'properties': len(info.properties),
                        'children': sorted(list(info.children))
                    }

        # Print classes sorted alphabetically
        for class_name, info in sorted(addon_classes.items()):
            print(f"\n  {class_name} [{info['source']}]")
            if info['parent']:
                print(f"    ├── Inherits from: {info['parent']}")
            if info['children']:
                print(f"    ├── Children: {', '.join(info['children'])}")
            print(f"    └── Properties: {info['properties']}")

def write_class_hierarchy(hierarchies: Dict[str, ClassHierarchy], output_file: Path) -> None:
    """Write tree visualization of class hierarchies to file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        def write_tree(classes: Dict[str, Any], root_classes: Set[str], indent: str = "") -> None:
            for class_name in sorted(root_classes):
                info = classes.get(class_name)
                if not info:
                    continue
                    
                prop_count = len(info.properties)
                f.write(f"{indent}├── {class_name} ({prop_count} properties)\n")
                
                important_props = {'scope', 'model', 'displayName', 'type', 'baseClass'}
                found_props = {k: v for k, v in sorted(info.properties.items()) if k in important_props}
                if found_props:
                    for prop, value in sorted(found_props.items()):
                        f.write(f"{indent}│   ├── {prop} = {value}\n")
                
                if info.children:
                    write_tree(classes, sorted(info.children), indent + "│   ")

        f.write("\nClass Hierarchy by Source:\n")
        for source, hierarchy in sorted(hierarchies.items(), key=lambda x: x[0].lower()):
            f.write(f"\n=== {Path(source).name} ===\n")
            write_tree(hierarchy.classes, hierarchy.root_classes)

def write_inheritance_tree(hierarchies: Dict[str, ClassHierarchy], output_file: Path) -> None:
    """Write complete inheritance tree to file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        # Build a complete inheritance map
        inheritance_map = {}
        reverse_map = {}  # child -> parent mapping
        all_classes = set()
        
        # First pass: collect all classes and their relationships
        for source, hierarchy in hierarchies.items():
            for class_name, info in hierarchy.classes.items():
                all_classes.add(class_name)
                if info.parent:
                    if info.parent not in inheritance_map:
                        inheritance_map[info.parent] = set()
                    inheritance_map[info.parent].add(class_name)
                    reverse_map[class_name] = info.parent

        # Find root classes (no parent or parent not found)
        root_classes = {cls for cls in all_classes if cls not in reverse_map}

        def write_tree(class_name: str, indent: str = "", printed: Set[str] = None) -> None:
            if printed is None:
                printed = set()
                
            if class_name in printed:
                f.write(f"{indent}├── {class_name} (circular reference!)\n")
                return
                
            printed.add(class_name)
            children = inheritance_map.get(class_name, set())
            
            # Get class info from any hierarchy that contains this class
            class_info = None
            source_name = None
            for source, hierarchy in hierarchies.items():
                if class_name in hierarchy.classes:
                    class_info = hierarchy.classes[class_name]
                    source_name = Path(source).name
                    break

            # Write current class with details
            if class_info:
                props_count = len(class_info.properties)
                f.write(f"{indent}├── {class_name} ({props_count} properties) [{source_name}]\n")
                
                # Write important properties
                important_props = {'scope', 'model', 'displayName', 'type', 'baseClass'}
                found_props = {k: v for k, v in sorted(class_info.properties.items()) if k in important_props}
                if found_props:
                    for prop, value in sorted(found_props.items()):
                        f.write(f"{indent}│   ├── {prop} = {value}\n")
            else:
                f.write(f"{indent}├── {class_name} (reference only)\n")

            # Write children
            for child in sorted(children):
                write_tree(child, indent + "│   ", printed)

        # Write complete inheritance tree
        f.write("\nComplete Class Inheritance Tree:\n")
        f.write("Legend: ClassName (property count) [source PBO]\n")
        f.write("────────────────────────────────────────────\n")
        
        for root in sorted(root_classes):
            write_tree(root)
            f.write("────────────────────────────────────────────\n")

def write_addon_hierarchies(hierarchies: Dict[str, ClassHierarchy], output_file: Path) -> None:
    """Write class hierarchies grouped by addon folders to file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        # Group hierarchies by addon folder
        addon_groups = {}
        
        for source, hierarchy in hierarchies.items():
            path = Path(source)
            # Find addon root (starts with @)
            addon_root = None
            for parent in path.parents:
                if parent.name.startswith('@'):
                    addon_root = parent.name
                    break
            
            # Group by addon or 'Base Game' if no @ folder
            group_key = addon_root or 'Base Game'
            if group_key not in addon_groups:
                addon_groups[group_key] = {}
            addon_groups[group_key][source] = hierarchy

        # Write each addon's classes
        f.write("\nClasses by Addon:\n")
        f.write("=================\n")
        
        for addon_name, sources in sorted(addon_groups.items()):
            f.write(f"\n{addon_name}\n")
            f.write("─" * len(addon_name) + "\n")
            
            # Collect all classes for this addon
            addon_classes = {}
            for source, hierarchy in sources.items():
                for class_name, info in hierarchy.classes.items():
                    if class_name not in addon_classes:
                        addon_classes[class_name] = {
                            'source': Path(source).name,
                            'parent': info.parent,
                            'properties': len(info.properties),
                            'children': sorted(list(info.children))
                        }

            # Write classes sorted alphabetically
            for class_name, info in sorted(addon_classes.items()):
                f.write(f"\n  {class_name} [{info['source']}]\n")
                if info['parent']:
                    f.write(f"    ├── Inherits from: {info['parent']}\n")
                if info['children']:
                    f.write(f"    ├── Children: {', '.join(info['children'])}\n")
                f.write(f"    └── Properties: {info['properties']}\n")

def generate_class_report(api: ClassAPI, scan_results: Dict[str, ClassHierarchy], output_dir: Path) -> None:
    """Generate detailed reports focusing on class definitions and hierarchies"""
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Define output files
    json_file = output_dir / f"class_scan_{timestamp}.json"
    hierarchy_file = output_dir / f"class_hierarchy_{timestamp}.txt"
    inheritance_file = output_dir / f"inheritance_tree_{timestamp}.txt"
    addon_file = output_dir / f"addon_classes_{timestamp}.txt"
    summary_file = output_dir / f"summary_{timestamp}.txt"

    # Initialize statistics
    stats = {
        'total_files': len(scan_results),
        'total_classes': 0,
        'inheritance_chains': {},
        'class_types': {
            'base_classes': set(),    # Classes with no parent
            'derived_classes': set(), # Classes that inherit from others
            'cfg_classes': set(),     # Classes starting with Cfg
            'ui_classes': set(),      # UI-related classes
        },
        'common_properties': {},      # Properties that appear in multiple classes
        'complex_classes': [],        # Classes with most properties
    }
    
    property_usage = {}  # Track property usage across classes
    
    # Analyze hierarchies
    for source, hierarchy in scan_results.items():
        for class_name, info in hierarchy.classes.items():
            stats['total_classes'] += 1
            
            # Track class types
            if not info.parent:
                stats['class_types']['base_classes'].add(class_name)
            else:
                stats['class_types']['derived_classes'].add(class_name)
                
            if class_name.startswith('Cfg'):
                stats['class_types']['cfg_classes'].add(class_name)
            elif class_name.startswith(('Rsc', 'IGU')):
                stats['class_types']['ui_classes'].add(class_name)
            
            # Track inheritance chains
            if info.parent:
                if info.parent not in stats['inheritance_chains']:
                    stats['inheritance_chains'][info.parent] = set()
                stats['inheritance_chains'][info.parent].add(class_name)
            
            # Track property usage
            for prop in info.properties:
                if prop not in property_usage:
                    property_usage[prop] = set()
                property_usage[prop].add(class_name)
            
            # Track complex classes
            stats['complex_classes'].append((class_name, len(info.properties)))
    
    # Sort complex classes by property count
    stats['complex_classes'].sort(key=lambda x: x[1], reverse=True)
    stats['complex_classes'] = stats['complex_classes'][:50]  # Keep top 50
    
    # Find common properties (used in multiple classes)
    stats['common_properties'] = {
        prop: list(classes)
        for prop, classes in property_usage.items()
        if len(classes) > 1
    }
    
    # Convert sets to lists for JSON serialization
    for key in stats['class_types']:
        stats['class_types'][key] = list(stats['class_types'][key])
    
    for parent in stats['inheritance_chains']:
        stats['inheritance_chains'][parent] = list(stats['inheritance_chains'][parent])

    report = {
        "scan_time": datetime.now().isoformat(),
        "summary": {
            "total_files_scanned": stats['total_files'],
            "total_classes_found": stats['total_classes'],
            "base_classes": len(stats['class_types']['base_classes']),
            "derived_classes": len(stats['class_types']['derived_classes']),
            "cfg_classes": len(stats['class_types']['cfg_classes']),
            "ui_classes": len(stats['class_types']['ui_classes'])
        },
        "class_types": stats['class_types'],
        "inheritance_chains": stats['inheritance_chains'],
        "common_properties": stats['common_properties'],
        "complex_classes": stats['complex_classes'],
        "hierarchies": {
            source: {
                "root_classes": sorted(list(h.root_classes)),
                "classes": {
                    name: {
                        "parent": info.parent,
                        "children": sorted(list(info.children)),
                        "properties": dict(sorted(info.properties.items())),
                        "inherited_properties": dict(sorted(info.inherited_properties.items()))
                    }
                    for name, info in sorted(h.classes.items())
                }
            }
            for source, h in sorted(scan_results.items())
        }
    }
    
    # Write all reports to files silently
    write_class_hierarchy(scan_results, hierarchy_file)
    write_inheritance_tree(scan_results, inheritance_file)
    write_addon_hierarchies(scan_results, addon_file)
    
    # Write JSON report
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, sort_keys=True)

    # Write summary to separate file
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Scan Summary ({datetime.now().isoformat()})\n")
        f.write("="*50 + "\n")
        f.write(f"Total Files Scanned: {stats['total_files']}\n")
        f.write(f"Total Classes Found: {stats['total_classes']}\n\n")
        
        f.write("Class Types:\n")
        f.write(f"  Base Classes: {len(stats['class_types']['base_classes'])}\n")
        f.write(f"  Derived Classes: {len(stats['class_types']['derived_classes'])}\n")
        f.write(f"  Config Classes: {len(stats['class_types']['cfg_classes'])}\n")
        f.write(f"  UI Classes: {len(stats['class_types']['ui_classes'])}\n\n")
        
        f.write("Most Inherited Classes:\n")
        inheritance_counts = {
            parent: len(children) 
            for parent, children in stats['inheritance_chains'].items()
        }
        for parent, count in sorted(inheritance_counts.items(), key=lambda x: (-x[1], x[0]))[:10]:
            f.write(f"  {parent}: {count} children\n")
        
        f.write("\nMost Complex Classes:\n")
        for class_name, prop_count in stats['complex_classes'][:10]:
            f.write(f"  {class_name}: {prop_count} properties\n")

    # Only print file locations
    logger.info(f"Reports written to: {output_dir}")

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

def main():
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Scan Arma 3 and mods for class definitions')
    parser.add_argument('--game', type=Path, default=DEFAULT_ARMA3_PATH, help='Path to Arma 3 directory')
    parser.add_argument('--mods', type=Path, default=DEFAULT_MODS_PATH, help='Path to Arma 3 mods directory')
    args = parser.parse_args()

    # Setup directories and logging
    temp_dir = ensure_temp_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = temp_dir / f"class_scan_{timestamp}.json"
    log_file = temp_dir / f"scan_{timestamp}.log"

    # Setup logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    handlers = [
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
    
    for handler in handlers:
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    try:
        # Initialize API with configuration
        config = ClassAPIConfig(
            cache_max_age=3600,  # 1 hour cache
            scan_timeout=120     # 2 minutes timeout per file
        )
        api = ClassAPI(config)
        logger.info(f"Output will be saved to: {temp_dir}")
        
        # Perform scans
        with tqdm(desc="Scanning", unit=" files") as pbar:
            def progress_callback(file_path: str):
                pbar.update(1)
                pbar.set_description(f"Scanning: {Path(file_path).name[:30]}")
            
            # Set progress callback
            api.set_progress_callback(progress_callback)
            
            # Scan directories
            results = scan_game_folders(api, args.game, args.mods, logger)
            
        # Generate and save report
        generate_class_report(api, results, temp_dir)
        
    except KeyboardInterrupt:
        logger.error("\nScan interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"\nError during scan: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        api.clear_cache()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

if __name__ == "__main__":
    main()
