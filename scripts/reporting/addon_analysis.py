from pathlib import Path
from typing import Dict
from class_scanner import ClassHierarchy

def write_addon_hierarchies(hierarchies: Dict[str, ClassHierarchy], output_file: Path) -> None:
    """Write class hierarchies grouped by addon folders to file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        addon_groups = group_by_addon(hierarchies)
        
        f.write("\nClasses by Addon:\n")
        f.write("=================\n")
        
        for addon_name, sources in sorted(addon_groups.items()):
            f.write(f"\n{addon_name}\n")
            f.write("─" * len(addon_name) + "\n")
            
            addon_classes = collect_addon_classes(sources)
            
            # Write classes sorted alphabetically
            for class_name, info in sorted(addon_classes.items()):
                f.write(f"\n  {class_name} [{info['source']}]\n")
                if info['parent']:
                    f.write(f"    ├── Inherits from: {info['parent']}\n")
                if info['children']:
                    f.write(f"    ├── Children: {', '.join(info['children'])}\n")
                f.write(f"    └── Properties: {info['properties']}\n")

def group_by_addon(hierarchies: Dict[str, ClassHierarchy]) -> Dict[str, Dict[str, ClassHierarchy]]:
    """Group hierarchies by addon folder"""
    addon_groups = {}
    
    for source, hierarchy in hierarchies.items():
        path = Path(source)
        addon_root = None
        for parent in path.parents:
            if parent.name.startswith('@'):
                addon_root = parent.name
                break
        
        group_key = addon_root or 'Base Game'
        if group_key not in addon_groups:
            addon_groups[group_key] = {}
        addon_groups[group_key][source] = hierarchy
    
    return addon_groups

def collect_addon_classes(sources: Dict[str, ClassHierarchy]) -> Dict[str, dict]:
    """Collect all classes for an addon"""
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
    return addon_classes
