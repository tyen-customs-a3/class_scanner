import logging
import pytest
from src.parser.class_parser import ClassParser

from .conftest import TEST_DATA

logger = logging.getLogger(__name__)

@pytest.fixture
def headband_config() -> str:
    path = TEST_DATA['headband']['source_path']
    with open(path) as f:
        return f.read()

def test_headband_config_structure(parser: ClassParser, headband_config: str) -> None:
    """Test parsing produces correct data structures"""
    result = parser.parse_class_definitions(headband_config)
    
    assert 'CfgPatches' in result
    assert 'CfgWeapons' in result

def test_headband_patches_class(parser: ClassParser, headband_config: str) -> None:
    """Test CfgPatches basic structure"""
    result = parser.parse_class_definitions(headband_config)
    patches = result['CfgPatches']
    
    assert 'tc_rhs_headband' in patches

def test_headband_weapons_inheritance(parser: ClassParser, headband_config: str) -> None:
    """Test basic inheritance structure"""
    result = parser.parse_class_definitions(headband_config)
    weapons = result['CfgWeapons']
    
    # Check against TEST_DATA inheritance
    headband_data = TEST_DATA['headband']['expected_classes']
    for class_name, expected in headband_data.items():
        if class_name in weapons:
            assert weapons[class_name]['parent'] == expected['parent'], \
                f"Wrong parent for {class_name}, expected {expected['parent']}"
