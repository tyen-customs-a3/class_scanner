import pytest
from pathlib import Path
from src.scanner import ClassScanner
from src.models import PboClasses, ClassData

def test_scan_pca_quick():
    """Integration test scanning c:/pca_quick directory for PBOs"""
    scanner = ClassScanner()
    directory = Path("c:/pca_quick")
    
    # Ensure directory exists
    assert directory.exists(), "c:/pca_quick directory not found"
    
    # Scan directory
    results = scanner.scan_directory(directory)
    assert results, "No results found"
    
    print(f"\nFound {len(results)} PBO files:")
    
    # Analyze results
    total_classes = 0
    inheritance_chains = set()
    
    for pbo_path, pbo_data in results.items():
        print(f"\nPBO: {pbo_path}")
        print(f"Classes found: {len(pbo_data.classes)}")
        total_classes += len(pbo_data.classes)
        
        # Track inheritance chains
        for class_name, class_data in pbo_data.classes.items():
            if class_data.parent:
                inheritance_chains.add(f"{class_data.parent} -> {class_name}")
    
    print(f"\nTotal classes found: {total_classes}")
    print("\nSample inheritance chains:")
    for chain in sorted(list(inheritance_chains)[:10]):  # Show first 10 chains
        print(chain)
        
    assert total_classes > 0, "No classes found in any PBO"
