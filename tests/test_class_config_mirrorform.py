import logging
import pytest
from pathlib import Path

from parser import ClassParser
from .conftest import TEST_DATA

logger = logging.getLogger(__name__)

@pytest.fixture
def test_file() -> str:
    path = TEST_DATA['mirror']['config_path']
    with open(path) as f:
        return f.read()

def test_mirror_config_structure(parser: ClassParser, test_file: str) -> None:
    """Test parsing produces correct data structures"""
    result = parser.parse_class_definitions(test_file)
    
    # Check only for existence of main classes
    assert 'CfgPatches' in result
    assert 'CfgWeapons' in result
    assert 'CfgVehicles' in result

def test_mirror_patches_class(parser: ClassParser, test_file: str) -> None:
    """Test CfgPatches basic structure"""
    result = parser.parse_class_definitions(test_file)
    patches = result['CfgPatches']
    
    # Check only class existence
    assert 'TC_MIRROR' in patches

def test_mirror_inheritance(parser: ClassParser, test_file: str) -> None:
    """Test basic inheritance relationships"""
    result = parser.parse_class_definitions(test_file)
    mirror_data = TEST_DATA['mirror']['expected_classes']
    
    # Check Weapons and Vehicles classes
    for section in ['CfgWeapons', 'CfgVehicles']:
        if section in result:
            section_classes = result[section]
            for class_name, expected in mirror_data.items():
                if class_name in section_classes:
                    assert section_classes[class_name]['parent'] == expected['parent'], \
                        f"Wrong parent for {class_name}, expected {expected['parent']}"
