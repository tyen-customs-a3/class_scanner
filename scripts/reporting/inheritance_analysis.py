from pathlib import Path
from typing import Dict, Set
from class_scanner import ClassHierarchy

def build_inheritance_map(hierarchies: Dict[str, ClassHierarchy]) -> tuple[dict, dict, set]:
    """Build complete inheritance mapping"""
    inheritance_map = {}
    reverse_map = {}  # child -> parent mapping
    all_classes = set()
    
    for source, hierarchy in hierarchies.items():
        for class_name, info in hierarchy.classes.items():
            all_classes.add(class_name)
            if info.parent:
                if info.parent not in inheritance_map:
                    inheritance_map[info.parent] = set()
                inheritance_map[info.parent].add(class_name)
                reverse_map[class_name] = info.parent
                
    return inheritance_map, reverse_map, all_classes

def write_inheritance_tree(hierarchies: Dict[str, ClassHierarchy], output_file: Path) -> None:
    """Write complete inheritance tree to file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        inheritance_map, reverse_map, all_classes = build_inheritance_map(hierarchies)
        root_classes = {cls for cls in all_classes if cls not in reverse_map}

        def write_tree(class_name: str, indent: str = "", printed: Set[str] = None) -> None:
            if printed is None:
                printed = set()
                
            if class_name in printed:
                f.write(f"{indent}├── {class_name} (circular reference!)\n")
                return
                
            printed.add(class_name)
            children = inheritance_map.get(class_name, set())
            
            class_info = None
            source_name = None
            for source, hierarchy in hierarchies.items():
                if class_name in hierarchy.classes:
                    class_info = hierarchy.classes[class_name]
                    source_name = Path(source).name
                    break

            if class_info:
                props_count = len(class_info.properties)
                f.write(f"{indent}├── {class_name} ({props_count} properties) [{source_name}]\n")
                
                important_props = {'scope', 'model', 'displayName', 'type', 'baseClass'}
                found_props = {k: v for k, v in sorted(class_info.properties.items()) if k in important_props}
                if found_props:
                    for prop, value in sorted(found_props.items()):
                        f.write(f"{indent}│   ├── {prop} = {value}\n")
            else:
                f.write(f"{indent}├── {class_name} (reference only)\n")

            for child in sorted(children):
                write_tree(child, indent + "│   ", printed)

        f.write("\nComplete Class Inheritance Tree:\n")
        f.write("Legend: ClassName (property count) [source PBO]\n")
        f.write("────────────────────────────────────────────\n")
        
        for root in sorted(root_classes):
            write_tree(root)
            f.write("────────────────────────────────────────────\n")
