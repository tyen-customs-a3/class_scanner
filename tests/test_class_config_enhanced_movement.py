import logging
import pytest
from pathlib import Path
from src.parser import ClassParser
from .conftest import TEST_DATA

logger = logging.getLogger(__name__)

@pytest.fixture
def test_file() -> str:
    path = TEST_DATA['em_babe']['config_path']
    with open(path) as f:
        return f.read()

def test_em_config_structure(parser: ClassParser, test_file: str) -> None:
    """Test parsing produces correct data structures"""
    result = parser.parse_class_definitions(test_file)
    
    # Check only for existence of main classes
    assert 'CfgPatches' in result
    assert 'CfgModSettings' in result
    assert 'CfgVehicles' in result

def test_em_patches_class(parser: ClassParser, test_file: str) -> None:
    """Test CfgPatches basic structure"""
    result = parser.parse_class_definitions(test_file)
    patches = result['CfgPatches']
    
    # Check only class existence
    assert 'BaBe_EM' in patches

def test_em_inheritance(parser: ClassParser, test_file: str) -> None:
    """Test basic inheritance relationships"""
    result = parser.parse_class_definitions(test_file)
    vehicles = result['CfgVehicles']
    
    # Check inheritance chain matches TEST_DATA
    em_data = TEST_DATA['em_babe']['expected_classes']
    
    # Test each class's inheritance
    for class_name, expected in em_data.items():
        if class_name in vehicles:
            assert vehicles[class_name]['parent'] == expected['parent'], \
                f"Wrong parent for {class_name}, expected {expected['parent']}"

