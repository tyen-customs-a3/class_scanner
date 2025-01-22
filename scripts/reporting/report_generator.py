import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging
from class_scanner import ClassAPI, ClassHierarchy

from .tree_visualization import write_tree_to_file
from .inheritance_analysis import write_inheritance_tree, build_inheritance_map
from .addon_analysis import write_addon_hierarchies
from .dependency_analysis import write_dependency_report

def collect_statistics(scan_results: Dict[str, ClassHierarchy]) -> Dict[str, Any]:
    """Collect comprehensive statistics about scanned classes"""
    stats = {
        'total_files': len(scan_results),
        'total_classes': 0,
        'inheritance_chains': {},
        'class_types': {
            'base_classes': set(),    
            'derived_classes': set(), 
            'cfg_classes': set(),     
            'ui_classes': set(),      
        },
        'common_properties': {},     
        'complex_classes': [],       
    }
    
    property_usage = {}
    
    for source, hierarchy in scan_results.items():
        for class_name, info in hierarchy.classes.items():
            stats['total_classes'] += 1
            
            if not info.parent:
                stats['class_types']['base_classes'].add(class_name)
            else:
                stats['class_types']['derived_classes'].add(class_name)
                
            if class_name.startswith('Cfg'):
                stats['class_types']['cfg_classes'].add(class_name)
            elif class_name.startswith(('Rsc', 'IGU')):
                stats['class_types']['ui_classes'].add(class_name)
            
            if info.parent:
                if info.parent not in stats['inheritance_chains']:
                    stats['inheritance_chains'][info.parent] = set()
                stats['inheritance_chains'][info.parent].add(class_name)
            
            for prop in info.properties:
                if prop not in property_usage:
                    property_usage[prop] = set()
                property_usage[prop].add(class_name)
            
            stats['complex_classes'].append((class_name, len(info.properties)))
    
    stats['complex_classes'].sort(key=lambda x: x[1], reverse=True)
    stats['complex_classes'] = stats['complex_classes'][:50]
    
    stats['common_properties'] = {
        prop: list(classes)
        for prop, classes in property_usage.items()
        if len(classes) > 1
    }
    
    return stats

def generate_class_report(api: ClassAPI, scan_results: Dict[str, ClassHierarchy], output_dir: Path) -> None:
    """Generate comprehensive class analysis reports"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = output_dir / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Define output files with simpler names
    files = {
        'json': report_dir / "scan.json",
        'hierarchy': report_dir / "hierarchy.txt",
        'inheritance': report_dir / "inheritance.txt",
        'addon': report_dir / "addons.txt",
        'summary': report_dir / "summary.txt",
        'dependencies': report_dir / "dependencies.txt"  # Add new report file
    }

    # Collect statistics
    stats = collect_statistics(scan_results)
    
    # Prepare report data
    report = {
        "scan_time": datetime.now().isoformat(),
        "summary": {
            "total_files_scanned": stats['total_files'],
            "total_classes_found": stats['total_classes'],
            "base_classes": len(stats['class_types']['base_classes']),
            "derived_classes": len(stats['class_types']['derived_classes']),
            "cfg_classes": len(stats['class_types']['cfg_classes']),
            "ui_classes": len(stats['class_types']['ui_classes'])
        }
    }
    
    # Convert sets to lists for JSON serialization
    for key in stats['class_types']:
        stats['class_types'][key] = list(stats['class_types'][key])
    
    for parent in stats['inheritance_chains']:
        stats['inheritance_chains'][parent] = list(stats['inheritance_chains'][parent])
    
    report.update({
        "class_types": stats['class_types'],
        "inheritance_chains": stats['inheritance_chains'],
        "common_properties": stats['common_properties'],
        "complex_classes": stats['complex_classes'],
        "hierarchies": {
            source: {
                "root_classes": sorted(list(h.root_classes)),
                "classes": {
                    name: {
                        "parent": info.parent,
                        "children": sorted(list(info.children)),
                        "properties": dict(sorted(info.properties.items())),
                        "inherited_properties": dict(sorted(info.inherited_properties.items()))
                    }
                    for name, info in sorted(h.classes.items())
                }
            }
            for source, h in sorted(scan_results.items())
        }
    })

    # Generate all reports
    write_tree_to_file(scan_results, files['hierarchy'])
    write_inheritance_tree(scan_results, files['inheritance'])
    write_addon_hierarchies(scan_results, files['addon'])
    write_dependency_report(scan_results, files['dependencies'])  # Add dependency report
    
    with open(files['json'], 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, sort_keys=True)

    write_summary_file(stats, files['summary'])
    
    logging.getLogger().info(f"Reports written to: {report_dir}")

def write_summary_file(stats: Dict[str, Any], summary_file: Path) -> None:
    """Write summary statistics to file"""
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Scan Summary ({datetime.now().isoformat()})\n")
        f.write("="*50 + "\n")
        f.write(f"Total Files Scanned: {stats['total_files']}\n")
        f.write(f"Total Classes Found: {stats['total_classes']}\n\n")
        
        f.write("Class Types:\n")
        f.write(f"  Base Classes: {len(stats['class_types']['base_classes'])}\n")
        f.write(f"  Derived Classes: {len(stats['class_types']['derived_classes'])}\n")
        f.write(f"  Config Classes: {len(stats['class_types']['cfg_classes'])}\n")
        f.write(f"  UI Classes: {len(stats['class_types']['ui_classes'])}\n\n")
        
        f.write("Most Inherited Classes:\n")
        inheritance_counts = {
            parent: len(children) 
            for parent, children in stats['inheritance_chains'].items()
        }
        for parent, count in sorted(inheritance_counts.items(), key=lambda x: (-x[1], x[0]))[:10]:
            f.write(f"  {parent}: {count} children\n")
        
        f.write("\nMost Complex Classes:\n")
        for class_name, prop_count in stats['complex_classes'][:10]:
            f.write(f"  {class_name}: {prop_count} properties\n")
