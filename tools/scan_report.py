import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from threading import Lock
from typing import Dict, Any, List, TypedDict

from src.scanner import ClassScanner


class ClassInfo(TypedDict):
    name: str
    parent: str
    properties: Dict[str, Any]
    config_type: str
    category: str


class PboInfo(TypedDict):
    name: str
    class_count: int
    classes: List[ClassInfo]


class ReportData(TypedDict):
    timestamp: str
    total_pbos: int
    total_classes: int
    total_properties: int
    pbos: List[PboInfo]


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'type') and hasattr(obj, 'value'):
            return {
                'type': obj.type,
                'value': obj.value,
                'raw_value': getattr(obj, 'raw_value', None)
            }
        try:
            return dict(obj)
        except (TypeError, ValueError):
            try:
                return str(obj)
            except Exception:
                return repr(obj)


def scan_pbo(scanner: ClassScanner, pbo_path: Path, progress_callback=None) -> tuple[Path, Any]:
    """Scan a single PBO file"""
    if progress_callback:
        progress_callback(str(pbo_path))
    return pbo_path, scanner.scan_pbo(pbo_path)


def format_hierarchy_tree(class_name: str, level: int = 0, visited: set = None) -> List[str]:
    """Format hierarchy tree using arrow notation"""
    if visited is None:
        visited = set()
    if class_name in visited:
        return [f"{'  ' * level}↳ {class_name} [CYCLE]"]
    
    if not class_name:
        return []
        
    visited.add(class_name)
    lines = [f"{'  ' * level}↳ {class_name}" if level > 0 else class_name]
    
    child_set = children.get(class_name, set())
    if child_set is None:
        child_set = set()
    
    for child in sorted(child_set):
        if child:
            lines.extend(format_hierarchy_tree(child, level + 1, visited.copy()))
    
    return lines

def create_hierarchy_report(report_data: ReportData, output_path: Path) -> None:
    """Generate the hierarchy report with category-based grouping"""
    try:
        if not report_data or "pbos" not in report_data:
            logging.error("Invalid or empty report data")
            return
            
        lines = [
            "Class Scanner Report - Class Hierarchy",
            f"Generated: {report_data.get('timestamp', 'Unknown')}",
            "",
            "Class Hierarchy by Config Type:",
            "=========================="
        ]
        
        inheritance_map: Dict[str, Dict[str, set]] = {}
        container_map: Dict[str, Dict[str, set]] = {}
        class_info: Dict[str, Dict[str, str]] = {}
        all_parents = set()
        processed_classes = set()
        
        for pbo in report_data.get("pbos", []):
            if not isinstance(pbo, dict) or not pbo.get("classes"):
                continue
                
            for cls in pbo["classes"]:
                if not isinstance(cls, dict) or not cls.get("name"):
                    continue
                
                name = cls["name"]
                parent = cls.get("parent", "")
                container = cls.get("container", "")
                config_type = cls.get("config_type", "default")
                category = cls.get("category", "Uncategorized")
                
                class_info[name] = {
                    "config_type": config_type,
                    "category": category,
                    "parent": parent,
                    "container": container
                }
                
                if parent:
                    all_parents.add(parent)
                    if parent not in inheritance_map:
                        inheritance_map[parent] = {}
                    inheritance_map[parent].setdefault(config_type, set()).add(name)
                
                if container:
                    if container not in container_map:
                        container_map[container] = {}
                    container_map[container].setdefault(config_type, set()).add(name)
        
        for parent in all_parents:
            if parent not in class_info:
                config_types = {}
                for children_by_type in inheritance_map.get(parent, {}).values():
                    for child in children_by_type:
                        if child in class_info:
                            cfg_type = class_info[child]["config_type"]
                            config_types[cfg_type] = config_types.get(cfg_type, 0) + 1
                
                most_common_config = max(config_types.items(), key=lambda x: x[1])[0] if config_types else "default"
                
                class_info[parent] = {
                    "config_type": most_common_config,
                    "category": "External",
                    "parent": "",
                    "container": ""
                }
        
        for config_type in sorted(set(info["config_type"] for info in class_info.values())):
            lines.extend([
                f"\nConfig Type: {config_type}",
                "=" * (len(config_type) + 13)
            ])
            
            root_classes = {
                name for name, info in class_info.items()
                if info["config_type"] == config_type and (
                    not info["parent"] or 
                    info["parent"] not in class_info or
                    class_info[info["parent"]]["config_type"] != config_type
                )
            }
            
            def format_class_tree(class_name: str, level: int = 0, visited: set = None) -> List[str]:
                if visited is None:
                    visited = set()
                if class_name in visited:
                    return [f"{'  ' * level}↳ {class_name} [CYCLE]"]
                
                if class_name in processed_classes:
                    return []
                    
                visited.add(class_name)
                processed_classes.add(class_name)
                
                tag = " [External]" if class_info[class_name]["category"] == "External" else ""
                result = [f"{'  ' * level}↳ {class_name}{tag}" if level > 0 else class_name]
                
                children = set()
                if class_name in inheritance_map and config_type in inheritance_map[class_name]:
                    children.update(inheritance_map[class_name][config_type])
                if class_name in container_map and config_type in container_map[class_name]:
                    children.update(container_map[class_name][config_type])
                
                for child in sorted(children):
                    if child not in processed_classes:
                        result.extend(format_class_tree(child, level + 1, visited.copy()))
                
                return result
            
            for root in sorted(root_classes):
                if root not in processed_classes:
                    lines.extend(format_class_tree(root))
                    lines.append("")
                    
            processed_classes.clear()
        
        if not any(lines):
            lines.append("\nNo class hierarchies found.")
            
        try:
            output_path.write_text("\n".join(lines), encoding='utf-8')
        except Exception as e:
            logging.error(f"Error writing hierarchy report: {e}")
            
    except Exception as e:
        logging.error(f"Error in create_hierarchy_report: {e}")
        raise


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

    for pbo in report_data.get("pbos", []):
        if not isinstance(pbo, dict):
            continue
            
        name = pbo.get("name", "Unknown")
        classes = pbo.get("classes", [])
        class_count = len([c for c in classes if isinstance(c, dict) and "name" in c])
        
        lines.append(f"\n{name} ({class_count} classes):")
        for cls in sorted(classes, key=lambda x: x.get("name", "") if isinstance(x, dict) else ""):
            if isinstance(cls, dict) and "name" in cls:
                class_info = []
                class_info.append(f"  - {cls['name']}")
                
                if cls.get("parent"):
                    class_info.append(f"    Parent: {cls['parent']}")
                if cls.get("container"):
                    class_info.append(f"    Container: {cls['container']}")
                if cls.get("config_type"):
                    class_info.append(f"    Config Type: {cls['config_type']}")
                if cls.get("category"):
                    class_info.append(f"    Category: {cls['category']}")
                    
                lines.extend(class_info)

    try:
        output_path.write_text("\n".join(lines), encoding='utf-8')
    except Exception as e:
        logging.error(f"Error writing class list report: {e}")


def create_node_edge_report(report_data: ReportData, output_path: Path) -> None:
    """Generate a node-edge CSV report for class relationships"""
    try:
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
        
        # Write the CSV file
        lines = ["source;target"]
        lines.extend(f"{source};{target}" for source, target in sorted(edges))
        
        output_path.write_text("\n".join(lines), encoding='utf-8')
    except Exception as e:
        logging.error(f"Error writing node-edge report: {e}")


def create_report(scan_path: Path, output_dir: Path, max_workers: int = 4) -> None:
    """Create all report formats for PBO contents"""
    console = Console()
    scanner = ClassScanner()

    console.print(f"\n[bold blue]Scanning directory:[/] {scan_path}")

    pbo_files = list(scan_path.rglob("*.pbo"))
    if not pbo_files:
        console.print("[bold red]No PBOs found![/]")
        return

    progress_lock = Lock()
    with Progress() as progress:
        task = progress.add_task("[cyan]Scanning PBOs...", total=len(pbo_files))

        def progress_callback(msg):
            with progress_lock:
                progress.update(task, advance=1, description=f"[cyan]Scanning:[/] {Path(msg).name}")

        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(scan_pbo, scanner, Path(pbo), progress_callback)
                for pbo in pbo_files
            ]

            for future in as_completed(futures):
                try:
                    pbo_path, pbo_data = future.result()
                    if pbo_data and hasattr(pbo_data, 'classes'):
                        results[pbo_path] = pbo_data
                except Exception as e:
                    logging.error(f"Error scanning PBO: {e}")

    if not results:
        console.print("[bold red]No valid PBO data found![/]")
        return

    total_classes = 0
    total_properties = 0
    for pbo in results.values():
        if pbo and hasattr(pbo, 'classes'):
            total_classes += len(pbo.classes) if pbo.classes else 0
            if pbo.classes:
                total_properties += sum(
                    len(cls.properties) if hasattr(cls, 'properties') and cls.properties else 0
                    for cls in pbo.classes.values()
                )

    report_data: ReportData = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_pbos": len(results),
        "total_classes": total_classes,
        "total_properties": total_properties,
        "pbos": []
    }

    for pbo_path, pbo_data in results.items():
        if not hasattr(pbo_data, 'classes') or not pbo_data.classes:
            continue

        pbo_info: PboInfo = {
            "name": Path(pbo_path).name,
            "class_count": len(pbo_data.classes),
            "classes": []
        }

        for class_name, class_data in sorted(pbo_data.classes.items()):
            if not class_data:
                continue
                
            class_info: ClassInfo = {
                "name": class_name,
                "parent": getattr(class_data, 'parent', ''),
                "properties": getattr(class_data, 'properties', {}),
                "config_type": getattr(class_data, 'config_type', 'default'),
                "category": getattr(class_data, 'category', 'Uncategorized')
            }
            pbo_info["classes"].append(class_info)

        report_data["pbos"].append(pbo_info)

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        console.print(f"[bold red]Error creating output directory:[/] {e}")
        return

    try:
        json_path = output_dir / "report.json"
        json_path.write_text(
            json.dumps(report_data, indent=2, cls=CustomJSONEncoder),
            encoding='utf-8'
        )
    except Exception as e:
        console.print(f"[bold red]Error writing JSON report:[/] {e}")

    try:
        create_class_list_report(report_data, output_dir / "class_list.txt")
        create_hierarchy_report(report_data, output_dir / "hierarchy.txt")
        create_node_edge_report(report_data, output_dir / "node_edge.csv")
    except Exception as e:
        console.print(f"[bold red]Error generating reports:[/] {e}")
        return

    console.print("\n[bold green]Report generated successfully![/]")
    console.print(f"JSON Report: {json_path}")

    table = Table(title="Scan Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")
    table.add_row("PBOs Scanned", str(report_data["total_pbos"]))
    table.add_row("Total Classes", str(report_data["total_classes"]))
    table.add_row("Total Properties", str(report_data["total_properties"]))
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Generate detailed PBO scan reports")
    parser.add_argument("scan_path", type=Path, help="Directory to scan for PBOs")
    parser.add_argument("--output", "-o", type=Path, default=Path("reports"),
                        help="Output directory for reports (default: ./reports)")
    parser.add_argument("--threads", "-t", type=int, default=100,
                        help="Number of scanner threads (default: 100)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    create_report(args.scan_path, args.output, args.threads)


if __name__ == "__main__":
    main()
