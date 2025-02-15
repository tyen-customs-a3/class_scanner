import pytest
from pathlib import Path
from class_scanner.models import ClassData
from class_scanner.models import PropertyValue
from class_scanner.parser.class_parser import ClassParser

@pytest.fixture
def hierarchy_test_data() -> str:
    """Sample class configuration with nested hierarchies"""
    return """
    class CfgPatches {
        class TestMod {
            units[] = {};
            weapons[] = {};
        };
    };
    
    class CfgVehicles {
        class Car_Base;
        class Storage;
        
        class SportsCar: Car_Base {
            displayName = "Sports Car";
            class Cargo: Storage {
                displayName = "Cargo Space";
            };
        };
        
        class Truck: Car_Base {
            displayName = "Cargo Truck";
        };
    };
    
    class CfgWeapons {
        class Rifle_Base;
        class AssaultRifle: Rifle_Base {
            displayName = "AR";
        };
    };
    """

def test_class_hierarchy_tracking(parser: ClassParser, hierarchy_test_data: str) -> None:
    """Test that class hierarchies are correctly tracked"""
    result = parser.parse_class_definitions(hierarchy_test_data)
    
    # Check vehicles hierarchy
    vehicles = result['CfgVehicles']
    assert vehicles['SportsCar']['container'] == 'CfgVehicles'
    assert vehicles['Truck']['container'] == 'CfgVehicles'
    
    # Check weapons hierarchy
    weapons = result['CfgWeapons']
    assert weapons['AssaultRifle']['container'] == 'CfgWeapons'
    
    # Check patches hierarchy
    patches = result['CfgPatches']
    assert patches['TestMod']['container'] == 'CfgPatches'

def test_class_data_category_field() -> None:
    """Test that ClassData properly stores category information"""
    class_data = ClassData(
        name="SportsCar",
        parent="Car_Base",
        properties={
            "category": PropertyValue(
                name="category",
                raw_value="Cars"
            )
        },
        source_file=Path("config.cpp"),
        category="Cars"  # Now valid since category field exists
    )
    
    assert class_data.category == "Cars"
    assert class_data.properties["category"].value == "Cars"

def test_missing_category() -> None:
    """Test handling of classes without category field"""
    class_data = ClassData(
        name="BaseClass",
        parent="",
        properties={},
        source_file=Path("config.cpp")
    )
    
    assert class_data.category is None
    assert "category" not in class_data.properties

def test_nested_class_hierarchy(parser: ClassParser, hierarchy_test_data: str) -> None:
    """Test that class hierarchies are correctly tracked"""
    result = parser.parse_class_definitions(hierarchy_test_data)
    
    # Check vehicles hierarchy
    vehicles = result['CfgVehicles']
    
    # Check SportsCar and its nested Cargo class
    assert vehicles['SportsCar']['container'] == 'CfgVehicles'
    assert vehicles['Cargo']['container'] == 'SportsCar'
    assert vehicles['Cargo']['parent'] == 'Storage'
    assert vehicles['Cargo']['properties']['displayName'] == 'Cargo Space'  # PropertyValue equality operator will handle this

    # Check Truck
    assert vehicles['Truck']['container'] == 'CfgVehicles'
