import logging
import pytest
from typing import cast
from src.parser.class_parser import ClassParser, ConfigSections
from src.constants import (
    ConfigSectionName,
    CFG_PATCHES,
    CFG_WEAPONS,
    CFG_VEHICLES
)

from .conftest import TEST_DATA

logger = logging.getLogger(__name__)

@pytest.fixture
def test_file() -> str:
    path = TEST_DATA['mirror']['source_path']
    with open(path) as f:
        return f.read()

def _get_section(result: ConfigSections, section: ConfigSectionName):
    """Helper to access section dictionary with type safety"""
    return result[section]

def test_mirror_config_structure(parser: ClassParser, test_file: str) -> None:
    """Test parsing produces correct data structures"""
    result = parser.parse_class_definitions(test_file)
    
    # Check only for existence of main classes
    assert CFG_PATCHES in result
    assert CFG_WEAPONS in result
    assert CFG_VEHICLES in result

def test_mirror_patches_class(parser: ClassParser, test_file: str) -> None:
    """Test CfgPatches basic structure"""
    result = parser.parse_class_definitions(test_file)
    patches = _get_section(result, CFG_PATCHES)
    
    # Check only class existence
    assert 'TC_MIRROR' in patches

def test_mirror_inheritance(parser: ClassParser, test_file: str) -> None:
    """Test basic inheritance relationships"""
    result = parser.parse_class_definitions(test_file)
    mirror_data = TEST_DATA['mirror']['expected_classes']
    
    # Check Weapons and Vehicles classes
    sections = [CFG_WEAPONS, CFG_VEHICLES]
    for section in sections:
        section_name = cast(ConfigSectionName, section)
        if section_name in result:
            section_classes = _get_section(result, section_name)
            for class_name, expected in mirror_data.items():
                if class_name in section_classes:
                    assert section_classes[class_name]['parent'] == expected['parent'], \
                        f"Wrong parent for {class_name}, expected {expected['parent']}"
