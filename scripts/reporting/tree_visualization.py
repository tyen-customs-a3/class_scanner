from pathlib import Path
from typing import Dict, Any, Set
from class_scanner import ClassHierarchy

def print_class_hierarchy(hierarchies: Dict[str, ClassHierarchy]) -> None:
    """Print a tree visualization of class hierarchies"""
    def build_tree(classes: Dict[str, Any], root_classes: Set[str], indent: str = "") -> None:
        for class_name in sorted(root_classes):
            info = classes.get(class_name)
            if not info:
                continue
                
            prop_count = len(info.properties)
            print(f"{indent}├── {class_name} ({prop_count} properties)")
            
            important_props = {'scope', 'model', 'displayName', 'type', 'baseClass'}
            found_props = {k: v for k, v in sorted(info.properties.items()) if k in important_props}
            if found_props:
                for prop, value in sorted(found_props.items()):
                    print(f"{indent}│   ├── {prop} = {value}")
            
            if info.children:
                build_tree(classes, sorted(info.children), indent + "│   ")

    print("\nClass Hierarchy by Source:")
    for source, hierarchy in sorted(hierarchies.items(), key=lambda x: x[0].lower()):
        print(f"\n=== {Path(source).name} ===")
        build_tree(hierarchy.classes, hierarchy.root_classes)

def write_tree_to_file(hierarchies: Dict[str, ClassHierarchy], output_file: Path) -> None:
    """Write tree visualization to file"""
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
