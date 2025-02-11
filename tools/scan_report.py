import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
from class_scanner.scanner import Scanner
from reports.types import ClassInfo, PboInfo, ReportData
from reports.json_encoder import CustomJSONEncoder
from reports.class_list_report import create_class_list_report
from reports.hierarchy_report import create_hierarchy_report
from reports.node_edge_report import create_node_edge_report
from reports.targeted_inheritance_report import create_targeted_inheritance_report
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class PboScanner:
    def __init__(self, max_workers: int = 16):
        self.max_workers = max_workers
        self.console = Console()
        self.scanner = ClassScanner()
        self.progress_lock = Lock()

    def scan_pbo(self, pbo_path: Path, progress_callback=None) -> tuple[Path, Any]:
        if progress_callback:
            progress_callback(str(pbo_path))
        return pbo_path, self.scanner.scan_pbo(pbo_path)

    def scan_directory(self, scan_path: Path) -> Dict[Path, Any]:
        pbo_files = list(scan_path.rglob("*.pbo"))
        if not pbo_files:
            self.console.print("[bold red]No PBOs found![/]")
            return {}

        results = {}
        with Progress() as progress:
            task = progress.add_task("[cyan]Scanning PBOs...", total=len(pbo_files))

            def progress_callback(msg: str) -> None:
                with self.progress_lock:
                    progress.update(task, advance=1, description=f"[cyan]Scanning:[/] {Path(msg).name}")

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self.scan_pbo, Path(pbo), progress_callback)
                    for pbo in pbo_files
                ]

                for future in as_completed(futures):
                    try:
                        pbo_path, pbo_data = future.result()
                        if pbo_data and hasattr(pbo_data, 'classes'):
                            results[pbo_path] = pbo_data
                    except Exception as e:
                        logging.error(f"Error scanning PBO: {e}")

        return results

    def scan_multiple_directories(self, scan_paths: List[Path]) -> Dict[Path, Any]:
        """Scan multiple directories and combine the results"""
        all_results = {}
        total_pbos = sum(len(list(path.rglob("*.pbo"))) for path in scan_paths)

        if not total_pbos:
            self.console.print("[bold red]No PBOs found in any directory![/]")
            return {}

        with Progress() as progress:
            task = progress.add_task("[cyan]Scanning PBOs...", total=total_pbos)

            def progress_callback(msg: str) -> None:
                with self.progress_lock:
                    progress.update(task, advance=1, description=f"[cyan]Scanning:[/] {Path(msg).name}")

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for scan_path in scan_paths:
                    pbo_files = list(scan_path.rglob("*.pbo"))
                    futures.extend([
                        executor.submit(self.scan_pbo, Path(pbo), progress_callback)
                        for pbo in pbo_files
                    ])

                for future in as_completed(futures):
                    try:
                        pbo_path, pbo_data = future.result()
                        if pbo_data and hasattr(pbo_data, 'classes'):
                            all_results[pbo_path] = pbo_data
                    except Exception as e:
                        logging.error(f"Error scanning PBO: {e}")

        return all_results

    def build_class_info(self, class_name: str, class_data: Any) -> ClassInfo:
        return {
            "name": class_name,
            "parent": getattr(class_data, 'parent', ''),
            "properties": {
                name: {
                    'value': prop.value,
                    'raw_value': prop.raw_value,
                    'type': prop.value_type.name if prop.value_type else None,
                    'is_array': prop.is_array,
                    'array_values': prop.array_values
                } for name, prop in class_data.properties.items()
            },
            "config_type": getattr(class_data, 'config_type', 'default'),
            "category": getattr(class_data, 'category', 'Uncategorized'),
            "container": getattr(class_data, 'container', ''),
            "display_name": getattr(class_data, 'display_name', None)
        }

    def build_report_data(self, scan_results: Dict[Path, Any]) -> Optional[ReportData]:
        if not scan_results:
            return None

        total_classes = 0
        total_properties = 0
        pbos: List[PboInfo] = []

        for pbo_path, pbo_data in scan_results.items():
            if not hasattr(pbo_data, 'classes') or not pbo_data.classes:
                continue

            classes = []
            for class_name, class_data in sorted(pbo_data.classes.items()):
                if class_data:
                    classes.append(self.build_class_info(class_name, class_data))

            pbo_info: PboInfo = {
                "name": pbo_path.name,
                "class_count": len(classes),
                "classes": classes
            }
            pbos.append(pbo_info)

            total_classes += len(classes)
            total_properties += sum(
                len(cls["properties"]) for cls in classes
            )

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_pbos": len(pbos),
            "total_classes": total_classes,
            "total_properties": total_properties,
            "pbos": pbos
        }

    def print_summary(self, report_data: ReportData, json_path: Path) -> None:
        self.console.print("\n[bold green]Report generated successfully![/]")
        self.console.print(f"JSON Report: {json_path}")

        table = Table(title="Scan Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_row("PBOs Scanned", str(report_data["total_pbos"]))
        table.add_row("Total Classes", str(report_data["total_classes"]))
        table.add_row("Total Properties", str(report_data["total_properties"]))
        self.console.print(table)

    def generate_reports(self, report_data: ReportData, output_dir: Path, root_classes: List[str] = []) -> None:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            json_path = output_dir / "report.json"
            json_path.write_text(
                json.dumps(report_data, indent=2, cls=CustomJSONEncoder),
                encoding='utf-8'
            )

            if root_classes:
                create_targeted_inheritance_report(
                    report_data,
                    root_classes,
                    output_dir / "targeted_inheritance.csv"
                )

            self.print_summary(report_data, json_path)

        except Exception as e:
            self.console.print(f"[bold red]Error generating reports:[/] {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate detailed PBO scan reports")
    parser.add_argument("scan_paths", type=Path, nargs='+', help="Directories to scan for PBOs")
    parser.add_argument("--output", "-o", type=Path, default=Path("reports"), help="Output directory for reports (default: ./reports)")
    parser.add_argument("--threads", "-t", type=int, default=16,  help="Number of scanner threads (default: 16)")
    parser.add_argument("--verbose", "-v", action="store_true",  help="Enable verbose logging")
    parser.add_argument("--root-classes", "-r", type=str, nargs="+", help="Root class names to generate targeted inheritance reports")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    scanner = PboScanner(args.threads)

    scanner.console.print("\n[bold blue]Scanning directories:[/]")
    for path in args.scan_paths:
        scanner.console.print(f"  - {path}")

    results = scanner.scan_multiple_directories(args.scan_paths)
    if not results:
        scanner.console.print("[bold red]No valid PBO data found![/]")
        return

    report_data = scanner.build_report_data(results)
    if report_data:
        scanner.generate_reports(report_data, args.output, args.root_classes)


if __name__ == "__main__":
    main()
