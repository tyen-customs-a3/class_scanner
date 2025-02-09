import logging
from pathlib import Path
from .types import ReportData

def format_property_value(prop_data: dict) -> str:
    """Format property value for display"""
    if prop_data.get('is_array'):
        value = f"[{', '.join(str(v) for v in prop_data['array_values'])}]"
    else:
        value = str(prop_data.get('value', ''))
    
    if prop_data.get('type'):
        value += f" ({prop_data['type']})"
    return value

def create_class_list_report(report_data: ReportData, output_path: Path) -> None:
    """Generate the class list report with detailed class information"""
    if not report_data:
        logging.error("Invalid report data")
        return

    lines = [
        "Class Scanner Report - Full Class List",
        f"Generated: {report_data.get('timestamp', 'Unknown')}",
        "",
        f"Total PBOs: {report_data.get('total_pbos', 0)}",
        f"Total Classes: {report_data.get('total_classes', 0)}",
        f"Total Properties: {report_data.get('total_properties', 0)}",
        "",
        "Classes by PBO:",
        "=============="
    ]

    for pbo in sorted(report_data.get("pbos", []), key=lambda x: x.get("name", "")):
        name = pbo.get("name", "Unknown")
        classes = pbo.get("classes", [])
        
        if not classes:
            continue
            
        lines.append(f"\n{name} ({len(classes)} classes):")
        
        for cls in sorted(classes, key=lambda x: x.get("name", "")):
            if not cls.get("name"):
                continue
                
            # Basic class information
            lines.append(f"\n  {cls['name']}:")
            
            # Class attributes
            if cls.get("display_name"):
                lines.append(f"    Display Name: {cls['display_name']}")
            if cls.get("parent"):
                lines.append(f"    Parent: {cls['parent']}")
            if cls.get("container"):
                lines.append(f"    Container: {cls['container']}")
            if cls.get("config_type"):
                lines.append(f"    Config Type: {cls['config_type']}")
            if cls.get("category"):
                lines.append(f"    Category: {cls['category']}")
                
            # Properties section
            if cls.get("properties"):
                lines.append("    Properties:")
                for prop_name, prop_data in sorted(cls["properties"].items()):
                    value = format_property_value(prop_data)
                    lines.append(f"      {prop_name}: {value}")

    try:
        output_path.write_text("\n".join(lines), encoding='utf-8')
    except Exception as e:
        logging.error(f"Error writing class list report: {e}")
