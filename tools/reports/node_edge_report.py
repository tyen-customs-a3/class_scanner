import logging
from pathlib import Path
from typing import Set, Tuple
from .types import ReportData

def collect_edges(report_data: ReportData) -> Set[Tuple[str, str]]:
    """Collect all class relationships as edges"""
    edges = set()
    
    for pbo in report_data.get("pbos", []):
        if not isinstance(pbo, dict) or not pbo.get("classes"):
            continue
            
        for cls in pbo["classes"]:
            if not isinstance(cls, dict) or not cls.get("name"):
                continue
                
            source = cls["name"]
            
            # Add parent relationships
            if cls.get("parent"):
                edges.add((source, cls["parent"]))
                
            # Add container relationships
            if cls.get("container"):
                edges.add((source, cls["container"]))
                
    return edges

def create_node_edge_report(report_data: ReportData, output_path: Path) -> None:
    """Generate a node-edge CSV report for class relationships"""
    try:
        # Collect all edges
        edges = collect_edges(report_data)
        
        # Generate CSV content
        lines = ["source;target;type"]
        for source, target in sorted(edges):
            # Determine relationship type based on the data
            rel_type = "inherits_from"  # Default relationship type
            
            # Look up the actual relationship type
            for pbo in report_data.get("pbos", []):
                for cls in pbo.get("classes", []):
                    if cls.get("name") == source:
                        if cls.get("parent") == target:
                            rel_type = "inherits_from"
                        elif cls.get("container") == target:
                            rel_type = "contained_in"
                        break
            
            lines.append(f"{source};{target};{rel_type}")
        
        # Write the CSV file
        output_path.write_text("\n".join(lines), encoding='utf-8')
        
    except Exception as e:
        logging.error(f"Error writing node-edge report: {e}")
