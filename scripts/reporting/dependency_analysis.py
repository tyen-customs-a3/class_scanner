from pathlib import Path
from typing import Dict, Set, DefaultDict, Optional, Tuple
from collections import defaultdict
from class_scanner import ClassHierarchy

def get_mod_name(path: str) -> str:
    """Extract mod name from path"""
    path = Path(path)
    for parent in path.parents:
        if parent.name.startswith('@'):
            return parent.name
    return "Base Game"

def find_class_origin(class_name: str, hierarchies: Dict[str, ClassHierarchy]) -> Tuple[Optional[str], Optional[str]]:
    """Find where a class is first defined, following inheritance chain
    
    Returns:
        Tuple of (source path, mod name) where class originates, or (None, None) if not found
    """
    implementations = []
    inheritance_sources = {}
    
    # First, collect all implementations and build inheritance map
    for source, hierarchy in hierarchies.items():
        if class_name in hierarchy.classes:
            class_info = hierarchy.classes[class_name]
            implementations.append((source, class_info))
            
            # Track inheritance chain
            current = class_info.parent
            chain = []
            visited = {class_name}
            
            while current and current not in visited:
                chain.append(current)
                visited.add(current)
                if current in hierarchy.classes:
                    current = hierarchy.classes[current].parent
                else:
                    break
            
            if chain:
                inheritance_sources[source] = chain

    if not implementations:
        return None, None

    # First, check base game implementations
    base_impls = [impl for impl in implementations if get_mod_name(impl[0]) == "Base Game"]
    if base_impls:
        # Prefer implementation with no parent or parent in same source
        for source, info in base_impls:
            if not info.parent or (info.parent in hierarchies[source].classes):
                return source, "Base Game"
        # Fall back to first base game implementation
        return base_impls[0][0], "Base Game"

    # Then check mod implementations
    # Sort by mod name for consistent results
    sorted_impls = sorted(implementations, key=lambda x: get_mod_name(x[0]))
    
    # Look for implementations that define the class without external parent
    for source, info in sorted_impls:
        if not info.parent or (info.parent in hierarchies[source].classes):
            return source, get_mod_name(source)

    # If no definitive origin found, use the first implementation
    source, _ = sorted_impls[0]
    return source, get_mod_name(source)

def analyze_dependencies(hierarchies: Dict[str, ClassHierarchy]) -> Dict[str, Dict[str, Set[str]]]:
    """Analyze mod dependencies based on class inheritance"""
    # Build origin map for all classes
    class_origins = {}
    for source, hierarchy in hierarchies.items():
        for class_name in hierarchy.classes:
            if class_name not in class_origins:  # Only track first occurrence
                origin_source, origin_mod = find_class_origin(class_name, hierarchies)
                if origin_source and origin_mod:
                    class_origins[class_name] = origin_mod
    
    # Now analyze dependencies
    dependencies = defaultdict(lambda: defaultdict(set))
    
    for source, hierarchy in hierarchies.items():
        mod_name = get_mod_name(source)
        
        for class_name, info in hierarchy.classes.items():
            if info.parent and info.parent in class_origins:
                parent_mod = class_origins[info.parent]
                if parent_mod != mod_name:
                    # Store dependency only if parent is from different mod
                    dependencies[mod_name][parent_mod].add(
                        f"{class_name} -> {info.parent}"
                    )
    
    return dependencies

def write_dependency_report(hierarchies: Dict[str, ClassHierarchy], output_file: Path) -> None:
    """Write mod dependency report to file"""
    dependencies = analyze_dependencies(hierarchies)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Mod Dependencies Report\n")
        f.write("=====================\n\n")
        
        for mod_name in sorted(dependencies.keys()):
            f.write(f"\n{mod_name}\n")
            f.write("─" * len(mod_name) + "\n")
            
            if not dependencies[mod_name]:
                f.write("  No dependencies\n")
                continue
                
            for dep_mod, dep_classes in sorted(dependencies[mod_name].items()):
                f.write(f"\n  Depends on {dep_mod}:\n")
                for class_dep in sorted(dep_classes):
                    f.write(f"    {class_dep}\n")
