import argparse
import json
import logging
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional

from class_scanner.api import ClassAPI
from reports.types import ClassInfo, PboInfo, ReportData
from reports.json_encoder import CustomJSONEncoder
from reports.class_list_report import create_class_list_report
from reports.targeted_inheritance_report import create_targeted_inheritance_report
from reports.structure_report import create_structure_report

sys.path.insert(0, str(Path(__file__).parent.parent))

class GracefulInterruptHandler:
    def __init__(self):
        self.interrupted = False
        self.released = False
        self.original_handlers = {}

    def __enter__(self):
        self.interrupted = False
        self.released = False
        self.original_handlers = {
            sig: signal.getsignal(sig)
            for sig in (signal.SIGINT, signal.SIGTERM)
        }
        for sig in self.original_handlers:
            signal.signal(sig, self._handle_signal)
        return self

    def __exit__(self, *args, **kwargs):
        self.release()

    def _handle_signal(self, signum, frame):
        self.release()
        self.interrupted = True
        print("\nInterrupted by user. Cleaning up...", file=sys.stderr)

    def release(self):
        if self.released:
            return False

        for sig, handler in self.original_handlers.items():
            signal.signal(sig, handler)
        self.released = True
        return True

class ReportGenerator:
    def __init__(self, cache_dir: Optional[Path] = None, max_workers: int = 16):
        self.max_workers = max_workers
        self.api = ClassAPI(cache_dir=cache_dir)
        self._scanned = 0
        self._total = 0
        self._completed = 0
        self._errors = 0
        self._cached = 0
        self.interrupt_handler = GracefulInterruptHandler()

    def _progress_callback(self, msg: str) -> None:
        """Progress callback for individual PBO scanning"""
        self._scanned += 1
        print(f"\r[{self._completed + self._cached}/{self._total}] "
              f"Processing: {Path(msg).name:<50} "
              f"(Complete: {self._completed}, Cached: {self._cached}, Errors: {self._errors})", 
              end="", flush=True)

    def scan_directories(self, scan_paths: List[Path]) -> Dict[Path, Any]:
        """Scan multiple directories using multithreaded ClassAPI scanning"""
        # Collect all PBO files first
        pbo_files: List[Path] = []
        for path in scan_paths:
            pbo_files.extend(path.rglob("*.pbo"))

        if not pbo_files:
            print("No PBOs found in any directory!")
            return {}

        self._total = len(pbo_files)
        self._scanned = 0
        self._completed = 0
        self._errors = 0
        self._cached = 0
        
        print(f"\nFound {self._total} PBOs to process")
        print(f"Starting scan with {self.max_workers} threads...")

        # Set up progress tracking
        self.api.set_progress_callback(self._progress_callback)

        # Process PBOs in parallel
        results: Dict[Path, Any] = {}

        with self.interrupt_handler:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Create futures for each PBO file
                future_to_pbo = {
                    executor.submit(self.api.scan, pbo_file): pbo_file 
                    for pbo_file in pbo_files
                }

                try:
                    # Process completed scans
                    for future in as_completed(future_to_pbo):
                        if self.interrupt_handler.interrupted:
                            print("\nScan interrupted. Partial results will be saved.")
                            executor.shutdown(wait=False)
                            break

                        pbo_file = future_to_pbo[future]
                        try:
                            if scan_result := future.result():
                                results[pbo_file] = scan_result
                                self._completed += 1
                        except Exception as e:
                            self._errors += 1
                            print(f"\nError scanning {pbo_file}: {e}", file=sys.stderr)

                except KeyboardInterrupt:
                    print("\nReceived interrupt signal. Shutting down...", file=sys.stderr)
                    executor.shutdown(wait=False)
                    return results

        # Print final statistics
        print("\n\nScan completed:")
        print(f"  Successfully processed: {self._completed}")
        print(f"  Retrieved from cache:  {self._cached}")
        print(f"  Errors encountered:    {self._errors}")
        print(f"  Total PBOs:           {self._total}")

        if self.interrupt_handler.interrupted:
            print("  Note: Scan was interrupted - results are incomplete")

        return results

    def build_class_info(self, class_name: str, class_data: Any) -> ClassInfo:
        """Convert raw class data into report format"""
        return {
            "name": class_name,
            "parent": getattr(class_data, 'parent', ''),
            "properties": {
                name: {
                    'value': prop.value if hasattr(prop, 'value') else None,
                    'raw_value': prop.raw_value if hasattr(prop, 'raw_value') else None,
                    'type': prop.value_type.name if hasattr(prop, 'value_type') else None,
                    'is_array': prop.is_array if hasattr(prop, 'is_array') else False,
                    'array_values': prop.array_values if hasattr(prop, 'array_values') else []
                } for name, prop in class_data.properties.items()
            },
            "config_type": getattr(class_data, 'config_type', 'default'),
            "category": getattr(class_data, 'category', 'Uncategorized'),
            "container": getattr(class_data, 'container', ''),
            "display_name": getattr(class_data, 'display_name', class_name)
        }

    def build_report_data(self, scan_results: Dict[Path, Any]) -> Optional[ReportData]:
        """Generate report data structure from scan results"""
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
            total_properties += sum(len(cls["properties"]) for cls in classes)

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_pbos": len(pbos),
            "total_classes": total_classes,
            "total_properties": total_properties,
            "pbos": pbos
        }

    def print_summary(self, report_data: ReportData, json_path: Path) -> None:
        """Display scan results summary"""
        print("\nReport generated successfully!")
        print("\nReport files generated:")
        print("-" * 50)
        
        def print_report(name: str, path: Path) -> None:
            if path.exists():
                print(f"{name:<20} {path}")

        print_report("JSON Data", json_path)
        print_report("Structure", json_path.parent / "structure")
        print_report("Class List", json_path.parent / "class_list.txt")
        print_report("Hierarchy", json_path.parent / "hierarchy.txt")
        print_report("Node-Edge", json_path.parent / "node_edge.csv")
        if json_path.parent / "targeted_inheritance.csv" in json_path.parent.glob("*.csv"):
            print_report("Targeted Inheritance", json_path.parent / "targeted_inheritance.csv")
            
        print("\nScan Statistics:")
        print("-" * 50)
        print(f"{'PBOs Scanned:':<20} {report_data['total_pbos']}")
        print(f"{'Total Classes:':<20} {report_data['total_classes']}")
        print(f"{'Total Properties:':<20} {report_data['total_properties']}")

    def generate_reports(self, report_data: ReportData, output_dir: Path, root_classes: Optional[List[str]] = None) -> None:
        """Generate all report files"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Write main JSON report
            json_path = output_dir / "report.json"
            json_path.write_text(
                json.dumps(report_data, indent=2, cls=CustomJSONEncoder),
                encoding='utf-8'
            )

            # Generate structure report
            structure_dir = output_dir / "structure"
            create_structure_report(report_data, structure_dir)

            # Generate other reports
            create_class_list_report(report_data, output_dir / "class_list.txt")
            # create_hierarchy_report(report_data, output_dir / "hierarchy.txt")
            # create_node_edge_report(report_data, output_dir / "node_edge.csv")
            
            # Generate targeted inheritance report if root classes specified
            if root_classes:
                create_targeted_inheritance_report(
                    report_data,
                    root_classes,
                    output_dir / "targeted_inheritance.csv"
                )

            self.print_summary(report_data, json_path)

        except Exception as e:
            print(f"Error generating reports: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Generate detailed PBO scan reports")
    parser.add_argument("scan_paths", type=Path, nargs='+', help="Directories to scan for PBOs")
    parser.add_argument("--output", "-o", type=Path, default=Path("reports"), help="Output directory for reports")
    parser.add_argument("--cache-dir", "-c", type=Path, help="Cache directory for scan results")
    parser.add_argument("--threads", "-t", type=int, default=16, help="Number of scanner threads")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--root-classes", "-r", type=str, nargs="+", help="Root classes for inheritance report")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    try:
        generator = ReportGenerator(cache_dir=args.cache_dir, max_workers=args.threads)

        print("\nScanning directories:")
        for path in args.scan_paths:
            print(f"  - {path}")

        results = generator.scan_directories(args.scan_paths)
        if not results:
            print("No valid PBO data found!", file=sys.stderr)
            return

        report_data = generator.build_report_data(results)
        if report_data:
            generator.generate_reports(report_data, args.output, args.root_classes)

    except KeyboardInterrupt:
        print("\nProcess terminated by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
