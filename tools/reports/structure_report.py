import json
import logging
from pathlib import Path
from typing import Dict, Any
from .types import ReportData

def create_structure_report(report_data: ReportData, output_dir: Path) -> None:
    """Generate a folder structure mirroring the PBO organization"""
    try:
        if not report_data or not report_data.get("pbos"):
            return

        # Create base output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        for pbo in report_data["pbos"]:
            pbo_path = Path(pbo["name"])
            
            # Create addon folder structure
            addon_name = pbo_path.parent.name
            if addon_name.startswith('@'):
                structure_path = output_dir / addon_name / pbo_path.stem
            else:
                structure_path = output_dir / f"@{addon_name}" / pbo_path.stem
            
            structure_path.mkdir(parents=True, exist_ok=True)

            # Write class data
            classes_file = structure_path / "classes.json"
            class_data: Dict[str, Any] = {
                "pbo_name": pbo["name"],
                "class_count": pbo["class_count"],
                "classes": {
                    cls["name"]: {
                        "parent": cls.get("parent", ""),
                        "properties": cls.get("properties", {}),
                        "config_type": cls.get("config_type", "default"),
                        "category": cls.get("category", "Uncategorized"),
                        "display_name": cls.get("display_name", cls["name"])
                    }
                    for cls in pbo["classes"]
                }
            }
            
            classes_file.write_text(
                json.dumps(class_data, indent=2),
                encoding='utf-8'
            )

    except Exception as e:
        logging.error(f"Error creating structure report: {e}")
