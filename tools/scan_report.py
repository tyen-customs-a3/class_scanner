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

from src.models.core import PropertyData
from src.scanner import ClassScanner


class ClassInfo(TypedDict):
    name: str
    parent: str
    properties: Dict[str, Any]
    config_type: str


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


def format_hierarchy_tree(name: str, children: Dict[str, set], level: int = 0, visited: set[str] | None = set()) -> List[str]:
    """Format hierarchy tree using optimized dictionary approach"""
    if visited is None:
        visited = set()
    
    lines = []
    prefix = "│   " * (level-1) + "├── " if level > 0 else "╷"
    
    if name in visited:
        return [f"{prefix}{name} [CYCLE]"]
    
    visited.add(name)
    lines.append(f"{prefix}{name}")
    
    for child in sorted(children.get(name, set())):
        lines.extend(format_hierarchy_tree(child, children, level + 1, visited.copy()))
    
    return lines

def create_hierarchy_report(report_data: ReportData, output_path: Path) -> None:
    """Generate the hierarchy report with optimized processing"""
    lines = [
        "Class Scanner Report - Class Hierarchy",
        f"Generated: {report_data['timestamp']}",
        "",
        "Inheritance Structure by Config Type:",
        "================================"
    ]
    
    config_types: Dict[str, Dict[str, set]] = {}
    parents: Dict[str, str] = {}
    class_configs: Dict[str, str] = {}
    all_classes = set()
    
    for pbo in report_data["pbos"]:
        for cls in pbo["classes"]:
            if not isinstance(cls, dict):
                continue
                
            name = cls.get("name", "")
            parent = cls.get("parent", "")
            config_type = cls.get("config_type", "default")
            
            if not name:
                continue
                
            all_classes.add(name)
            class_configs[name] = config_type
            
            if parent:
                parents[name] = parent
                if config_type not in config_types:
                    config_types[config_type] = {}
                config_types[config_type].setdefault(parent, set()).add(name)
    
    for config_type in sorted(config_types.keys()):
        lines.extend([
            f"\nConfig Type: {config_type}",
            "=" * (len(config_type) + 13),
            ""
        ])
        
        children = config_types[config_type]
        config_classes = {cls for cls in all_classes if class_configs.get(cls) == config_type}
        
        root_classes = {
            cls for cls in config_classes 
            if cls not in parents or parents[cls] not in config_classes
        }
        
        for root in sorted(root_classes):
            lines.extend(format_hierarchy_tree(root, children))
            lines.append("")
    
    try:
        output_path.write_text("\n".join(lines), encoding='utf-8')
    except Exception as e:
        logging.error(f"Error writing hierarchy report: {e}")


def create_class_list_report(report_data: ReportData, output_path: Path) -> None:
    """Generate the class list report"""
    lines = [
        "Class Scanner Report - Full Class List",
        f"Generated: {report_data['timestamp']}",
        "",
        f"Total PBOs: {report_data['total_pbos']}",
        f"Total Classes: {report_data['total_classes']}",
        f"Total Properties: {report_data['total_properties']}",
        "",
        "Classes by PBO:",
        "=============="
    ]

    for pbo in report_data["pbos"]:
        lines.append(f"\n{pbo['name']} ({pbo['class_count']} classes):")
        for cls in pbo["classes"]:
            if isinstance(cls, dict) and "name" in cls:
                lines.append(f"  - {cls['name']}")

    try:
        output_path.write_text("\n".join(lines), encoding='utf-8')
    except Exception as e:
        logging.error(f"Error writing class list report: {e}")


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
                    if pbo_data:
                        results[pbo_path] = pbo_data
                except Exception as e:
                    logging.error(f"Error scanning PBO: {e}")

    if not results:
        console.print("[bold red]No PBOs found![/]")
        return

    report_data: ReportData = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_pbos": len(results),
        "total_classes": sum(len(pbo.classes) for pbo in results.values()),
        "total_properties": sum(
            sum(len(cls.properties) for cls in pbo.classes.values())
            for pbo in results.values()
        ),
        "pbos": []
    }

    for pbo_path, pbo_data in results.items():
        pbo_info: PboInfo = {
            "name": Path(pbo_path).name,
            "class_count": len(pbo_data.classes),
            "classes": []
        }

        for class_name, class_data in sorted(pbo_data.classes.items()):
            class_info: ClassInfo = {
                "name": class_name,
                "parent": class_data.parent,
                "properties": class_data.properties,
                "config_type": getattr(class_data, 'config_type', 'default')
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
