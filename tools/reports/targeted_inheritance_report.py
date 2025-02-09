import logging
from pathlib import Path
from typing import List, Set, Tuple
from .types import ReportData
from .inheritance_utils import InheritanceMapper


def create_targeted_inheritance_report(report_data: ReportData, root_classes: List[str], output_path: Path) -> None:
    """Generate CSV report for specific inheritance trees with source-target pairs"""
    try:
        mapper = InheritanceMapper(report_data)
        root_classes_set = set(root_classes)  # Convert to set for faster lookups

        valid_classes: Set[str] = set()
        inheritance_edges: Set[Tuple[str, str]] = set()

        # Process only classes that inherit from root classes
        for class_name in mapper.reverse_map:
            if mapper.inherits_from_any(class_name, root_classes_set):
                chain = mapper.get_inheritance_chain(class_name)
                valid_classes.add(class_name)
                
                # Build edges until we hit a root class
                for i in range(len(chain) - 1):
                    child, parent = chain[i], chain[i + 1]
                    valid_classes.add(parent)
                    inheritance_edges.add((child, parent))
                    if parent in root_classes_set:
                        break

        # Generate report
        lines = ["source;target;root_distance;inheritance_path"]
        
        for child, parent in sorted(inheritance_edges):
            chain = mapper.get_inheritance_chain(child)
            distance = len(chain) - 1
            path_str = " -> ".join(chain)
            lines.append(f"{child};{parent};{distance};{path_str}")

        output_path.write_text("\n".join(lines), encoding='utf-8')

    except Exception as e:
        logging.error(f"Error writing targeted inheritance report: {e}")
