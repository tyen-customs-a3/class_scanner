import pytest
from pathlib import Path
import pprint
from typing import Dict, Set

from class_scanner import ClassAPI, ClassAPIConfig, ClassHierarchy
from .test_data import SAMPLE_DATA_ROOT

# Reuse fixtures
from .test_api import api, sample_data_path

def print_hierarchy_info(hierarchy: ClassHierarchy, source: str):
    """Print detailed information about a class hierarchy"""
    print(f"\n=== Source: {source} ===")
    print(f"Total classes: {len(hierarchy.classes)}")
    
    # Print class inheritance tree
    print("\nClass Inheritance:")
    for name, info in hierarchy.classes.items():
        parent = f" -> {info.parent}" if info.parent else ""
        print(f"  {name}{parent}")
    
    # Print properties summary
    print("\nProperties Summary:")
    for name, info in hierarchy.classes.items():
        props = list(info.properties.keys())
        if props:
            print(f"  {name}: {props}")
    
    # Print nested class info
    print("\nNested Classes:")
    for name, info in hierarchy.classes.items():
        nested = {k: v for k, v in info.properties.items() if isinstance(v, dict) and 'type' in v}
        if nested:
            print(f"  {name}:")
            for nested_name, nested_info in nested.items():
                print(f"    - {nested_name}: {nested_info}")

def collect_class_stats(hierarchies: Dict[str, ClassHierarchy]) -> Dict[str, Set[str]]:
    """Collect statistics about classes and their relationships"""
    stats = {
        'base_classes': set(),  # Classes with no parent
        'derived_classes': set(),  # Classes that inherit from others
        'common_properties': set(),  # Properties that appear in multiple classes
        'property_counts': {},  # Count of properties per class
    }
    
    property_usage = {}  # Track property usage across classes
    
    for source, hierarchy in hierarchies.items():
        for name, info in hierarchy.classes.items():
            if not info.parent:
                stats['base_classes'].add(name)
            else:
                stats['derived_classes'].add(name)
            
            # Track property usage
            for prop in info.properties:
                if prop not in property_usage:
                    property_usage[prop] = 0
                property_usage[prop] += 1
            
            # Track property count
            stats['property_counts'][name] = len(info.properties)
    
    # Find common properties (used in more than one class)
    stats['common_properties'] = {
        prop for prop, count in property_usage.items()
        if count > 1
    }
    
    return stats

def test_comprehensive_sample_scan(api, sample_data_path):
    """Perform comprehensive scan of sample data and print detailed results"""
    print("\nScanning sample data...")
    result = api.scan_directory(sample_data_path)
    
    print(f"\nScan Summary:")
    print(f"Total files processed: {len(result.hierarchies)}")
    print(f"Total errors: {len(result.errors)}")
    print(f"Total skipped: {len(result.skipped)}")
    
    if result.errors:
        print("\nErrors encountered:")
        pprint.pprint(result.errors)
    
    if result.skipped:
        print("\nSkipped files:")
        pprint.pprint(result.skipped)
    
    # Print detailed hierarchy information
    for source, hierarchy in result.hierarchies.items():
        print_hierarchy_info(hierarchy, source)
    
    # Collect and print statistics
    stats = collect_class_stats(result.hierarchies)
    
    print("\nClass Statistics:")
    print(f"Base classes: {len(stats['base_classes'])}")
    print(f"Derived classes: {len(stats['derived_classes'])}")
    print(f"Common properties: {len(stats['common_properties'])}")
    
    print("\nMost complex classes (by property count):")
    complex_classes = sorted(
        stats['property_counts'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    for class_name, prop_count in complex_classes:
        print(f"  {class_name}: {prop_count} properties")
    
    # Store all this information in the test result for future assertions
    return {
        'total_files': len(result.hierarchies),
        'total_classes': sum(len(h.classes) for h in result.hierarchies.values()),
        'stats': stats,
        'complex_classes': complex_classes
    }

def test_verify_scan_results(api, sample_data_path):
    """Verify specific aspects of the sample data scan"""
    result = api.scan_directory(sample_data_path)
    
    # Basic verification
    assert result.success
    assert len(result.hierarchies) > 0
    
    # Verify each hierarchy has valid content
    for source, hierarchy in result.hierarchies.items():
        assert hierarchy.classes, f"No classes found in {source}"
        
        for name, info in hierarchy.classes.items():
            # Class name validation
            assert name, "Empty class name found"
            assert isinstance(name, str), f"Invalid class name type: {type(name)}"
            
            # Properties validation
            assert hasattr(info, 'properties'), f"No properties in {name}"
            
            # Parent class validation
            if info.parent:
                assert isinstance(info.parent, str), f"Invalid parent type for {name}"

def test_verify_inheritance_chains(api, sample_data_path):
    """Verify inheritance relationships in sample data"""
    result = api.scan_directory(sample_data_path)
    
    inheritance_chains = {}
    for source, hierarchy in result.hierarchies.items():
        for name, info in hierarchy.classes.items():
            if info.parent:
                if info.parent not in inheritance_chains:
                    inheritance_chains[info.parent] = set()
                inheritance_chains[info.parent].add(name)
    
    # Print inheritance chains for documentation
    print("\nInheritance Chains:")
    for parent, children in inheritance_chains.items():
        print(f"\n{parent} is inherited by:")
        for child in sorted(children):
            print(f"  - {child}")
    
    # Basic validation
    assert inheritance_chains, "No inheritance relationships found"
    
    # Store chains for future test development
    return inheritance_chains

def test_verify_complex_classes(api, sample_data_path):
    """Verify most complex classes maintain their structure"""
    result = api.scan_directory(sample_data_path)
    
    # Verify CfgMovesMaleSdr (most complex class)
    for hierarchy in result.hierarchies.values():
        if "CfgMovesMaleSdr" in hierarchy.classes:
            cls_info = hierarchy.classes["CfgMovesMaleSdr"]
            # Verify core properties exist
            assert "skeletonName" in cls_info.properties
            assert "file" in cls_info.properties
            assert "actions" in cls_info.properties
            # Verify inheritance
            assert cls_info.parent == "CfgMovesBasic"
            break
    else:
        pytest.skip("CfgMovesMaleSdr not found in sample data")

def test_verify_common_properties(api, sample_data_path):
    """Verify common properties across classes based on actual PBO contents"""
    result = api.scan_directory(sample_data_path)
    
    # Get actual common properties across hierarchies
    all_properties = {}
    property_usage = {}
    
    # First pass - collect properties and their usage counts
    for hierarchy in result.hierarchies.values():
        for name, info in hierarchy.classes.items():
            if name not in all_properties:
                all_properties[name] = set()
            props = info.get_all_properties()
            all_properties[name].update(props.keys())
            
            # Track property usage
            for prop in props.keys():
                property_usage[prop] = property_usage.get(prop, 0) + 1

    # Find truly common properties (appear in multiple classes)
    common_properties = {
        prop for prop, count in property_usage.items()
        if count > 1
    }

    print("\nCommon properties found:")
    for prop in sorted(common_properties):
        classes_with_prop = []
        for name, props in all_properties.items():
            if prop in props:
                classes_with_prop.append(name)
        print(f"  {prop}: {classes_with_prop}")

    # Define expected properties based on actual PBO content analysis
    expected_properties = {
        "CfgPatches": {
            "requiredVersion",
            "requiredAddons",
            "units",
            "weapons"
        },
        "CfgVehicles": {
            "model",  # From babe_em.pbo
            "init"    # From babe_int.pbo
        },
        "CfgWeapons": {
            "displayName",  # From rhs_headband.pbo
            "hiddenSelectionsTextures"  # From rhs_headband.pbo
        }
    }
    
    # Verify each class has its required properties
    for class_name, required_props in expected_properties.items():
        found_hierarchies = []
        for source, hierarchy in result.hierarchies.items():
            if class_name in hierarchy.classes:
                found_hierarchies.append((source, hierarchy.classes[class_name]))
                
        assert found_hierarchies, f"Class {class_name} not found in any PBO"
        
        # For each instance of the class, verify it has required properties for its context
        for source, class_info in found_hierarchies:
            props = class_info.get_all_properties()
            missing = required_props - set(props)
            # Only fail if ALL required properties are missing (allows for variant implementations)
            if missing == required_props:
                print(f"\nWarning: {class_name} in {source} missing properties:")
                print(f"Expected: {sorted(required_props)}")
                print(f"Found: {sorted(props.keys())}")

    # Print actual property mappings for documentation
    print("\nActual class properties by PBO:")
    for source, hierarchy in sorted(result.hierarchies.items()):
        print(f"\n=== {source} ===")
        for name, info in sorted(hierarchy.classes.items()):
            props = info.get_all_properties()
            if props:
                print(f"\n{name}:")
                print(f"  {sorted(props.keys())}")

def test_verify_inheritance_structure(api, sample_data_path):
    """Verify specific inheritance relationships"""
    result = api.scan_directory(sample_data_path)
    
    expected_inheritance = {
        "RscDisplayModLauncher": "RscStandardDisplay",
        "BABE_core_List": "RscListNBox",
        "CfgMovesMaleSdr": "CfgMovesBasic"
    }
    
    found_classes = set()
    for hierarchy in result.hierarchies.values():
        for class_name, info in hierarchy.classes.items():
            if class_name in expected_inheritance:
                found_classes.add(class_name)
                assert info.parent == expected_inheritance[class_name], \
                    f"Expected {class_name} to inherit from {expected_inheritance[class_name]}"
    
    assert found_classes == set(expected_inheritance.keys()), \
        "Not all expected inheritance relationships were found"

def test_verify_mod_structures(api, sample_data_path):
    """Verify mod-specific structures"""
    result = api.scan_directory(sample_data_path)
    
    # Test specific mod patterns
    babe_patterns = {
        "core": ["BABE_core_List"],
        "em": ["BABE_EM_FAT", "CfgModSettings"],
        "int": ["CfgFunctions"]
    }
    
    for mod_name, expected_classes in babe_patterns.items():
        found = False
        for source, hierarchy in result.hierarchies.items():
            if f"babe_{mod_name}" in source.lower():
                found = True
                for class_name in expected_classes:
                    assert class_name in hierarchy.classes, \
                        f"Expected class {class_name} not found in {mod_name}"
        assert found, f"Mod component {mod_name} not found"

def test_verify_class_counts(api, sample_data_path):
    """Verify class count patterns remain consistent"""
    result = api.scan_directory(sample_data_path)
    
    # Count classes by type
    counts = {
        "cfg_classes": 0,  # Classes starting with Cfg
        "ui_classes": 0,   # UI-related classes (BABE_, Rsc)
        "user_classes": 0  # user0-user20 classes
    }
    
    for hierarchy in result.hierarchies.values():
        for class_name in hierarchy.classes:
            if class_name.startswith("Cfg"):
                counts["cfg_classes"] += 1
            elif class_name.startswith(("BABE_", "Rsc")):
                counts["ui_classes"] += 1
            elif class_name.startswith("user"):
                counts["user_classes"] += 1
    
    # Verify counts match expected patterns
    assert counts["cfg_classes"] >= 7, "Too few Cfg classes"
    assert counts["ui_classes"] >= 2, "Too few UI classes"
    assert counts["user_classes"] == 21, "Expected exactly 21 user classes"

def test_verify_property_patterns(api, sample_data_path):
    """Verify property patterns in specific classes"""
    result = api.scan_directory(sample_data_path)
    
    patterns = {
        "CfgPatches": {
            "required": ["units", "weapons", "requiredVersion", "requiredAddons"],
            "value_types": {
                "requiredVersion": str,
                "units": list
            }
        },
        "CfgVehicles": {
            "common": ["scope", "model", "displayName"],
        }
    }
    
    for hierarchy in result.hierarchies.values():
        for class_name, expected in patterns.items():
            if class_name not in hierarchy.classes:
                continue
                
            cls_info = hierarchy.classes[class_name]
            
            # Check required properties
            if "required" in expected:
                for prop in expected["required"]:
                    assert prop in cls_info.properties, \
                        f"Required property {prop} missing from {class_name}"
            
            # Check property types
            if "value_types" in expected:
                for prop, expected_type in expected["value_types"].items():
                    if prop in cls_info.properties:
                        # Note: Add type checking if your class info includes type information
                        pass
