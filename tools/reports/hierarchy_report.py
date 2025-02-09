import logging
from pathlib import Path
from typing import Any, List
from .types import ReportData
from .inheritance_utils import InheritanceMapper


def format_class_tree(class_name: str, mapper: InheritanceMapper,
                      config_type: str, level: int = 0,
                      visited: set[Any] | None = None) -> List[str]:
    """Format a class hierarchy tree recursively"""
    if visited is None:
        visited = set()
    if class_name in visited:
        return [f"{'  ' * level}↳ {class_name} [CYCLE]"]

    visited.add(class_name)
    info = mapper.class_info.get(class_name, {})

    display_name = info.get("display_name", "")
    category = info.get("category", "")
    label = class_name
    if display_name:
        label += f" ({display_name})"
    if category == "External":
        label += " [External]"

    lines = [f"{'  ' * level}↳ {label}" if level > 0 else label]

    for child in sorted(mapper.get_all_children(class_name, config_type)):
        if child not in visited:
            lines.extend(format_class_tree(child, mapper, config_type, level + 1, visited.copy()))

    return lines


def create_hierarchy_report(report_data: ReportData, output_path: Path) -> None:
    """Generate the hierarchy report with category-based grouping"""
    try:
        if not report_data or "pbos" not in report_data:
            logging.error("Invalid or empty report data")
            return

        mapper = InheritanceMapper(report_data)

        lines = [
            "Class Scanner Report - Class Hierarchy",
            f"Generated: {report_data.get('timestamp', 'Unknown')}",
            "",
            "Class Hierarchy by Config Type:",
            "=========================="
        ]

        for config_type in mapper.get_config_types():
            lines.extend([
                f"\nConfig Type: {config_type}",
                "=" * (len(config_type) + 13)
            ])

            processed = set()
            for root in sorted(mapper.find_root_classes(config_type)):
                if root not in processed:
                    lines.extend(format_class_tree(root, mapper, config_type))
                    lines.append("")
                    processed.add(root)

        if not any(lines[4:]):
            lines.append("\nNo class hierarchies found.")

        output_path.write_text("\n".join(lines), encoding='utf-8')

    except Exception as e:
        logging.error(f"Error in create_hierarchy_report: {e}")
        raise
