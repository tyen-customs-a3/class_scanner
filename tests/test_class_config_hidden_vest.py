import logging
import pytest
from class_scanner.parser.class_parser import ClassParser

from .conftest import TEST_DATA

logger = logging.getLogger(__name__)

@pytest.fixture
def vest_config() -> str:
    path = TEST_DATA['hidden_vest']['source_path']
    with open(path) as f:
        return f.read()

def test_vest_config_structure(parser: ClassParser, vest_config: str) -> None:
    """Test parsing produces correct data structures"""
    result = parser.parse_class_definitions(vest_config)
    
    assert 'CfgWeapons' not in result

def test_vest_class_inheritance(parser: ClassParser, vest_config: str) -> None:
    """Test basic class inheritance"""
    result = parser.parse_class_definitions(vest_config)
    weapons = result['_global']
    
    # Check base vest
    assert 'pca_vest_invisible' in weapons
    assert weapons['pca_vest_invisible']['parent'] == 'Vest_Camo_Base'
    
    # Check plate vest
    assert 'pca_vest_invisible_plate' in weapons
    assert weapons['pca_vest_invisible_plate']['parent'] == 'pca_vest_invisible'

def test_vest_class_properties(parser: ClassParser, vest_config: str) -> None:
    """Test vest class properties"""
    result = parser.parse_class_definitions(vest_config)
    weapons = result['_global']
    
    vest = weapons['pca_vest_invisible']
    assert vest['properties']['scope'].raw_value == '2'
    assert vest['properties']['displayName'].raw_value == 'Invisible Vest'
    
    plate_vest = weapons['pca_vest_invisible_plate'] 
    assert plate_vest['properties']['scope'].raw_value == '2'
    assert plate_vest['properties']['displayName'].raw_value == 'Invisible Vest (Plate)'

def test_vest_section_detection(parser: ClassParser, vest_config: str) -> None:
    """Test that vests are properly detected as CfgWeapons"""
    result = parser.parse_class_definitions(vest_config)
    
    # All vests should be in CfgWeapons section
    assert 'pca_vest_invisible' in result['_global']
    assert 'pca_vest_invisible_kevlar' in result['_global']
    assert 'pca_vest_invisible_plate' in result['_global']
    
def test_loose_class_handling(parser: ClassParser, vest_config: str) -> None:
    """Test handling of classes without explicit sections"""
    result = parser.parse_class_definitions(vest_config)
    
    # Global section should contain loose classes
    globals = result['_global']
    assert len(globals) > 0
    
    # Verify inheritance still works
    vests = result['_global']
    assert 'pca_vest_invisible' in vests
    assert vests['pca_vest_invisible']['parent'] == 'Vest_Camo_Base'

def test_vest_section_validation(parser: ClassParser, vest_config: str) -> None:
    """Test that only required sections are present"""
    result = parser.parse_class_definitions(vest_config)
    
    # Should only have global section since no explicit Cfg* classes
    assert set(result.keys()) == {'_global'}
    
    # Verify CfgVehicles is not present
    assert 'CfgVehicles' not in result
