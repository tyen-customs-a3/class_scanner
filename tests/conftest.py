import pytest
import logging
from pathlib import Path
from typing import Dict, TypedDict
import sys
from pathlib import Path

from class_scanner.api import ClassAPI
from class_scanner.parser.class_parser import ClassParser

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Core test configuration 
ROOT_DIR = Path(__file__).parent.parent
TEST_DATA_ROOT = ROOT_DIR / 'tests' / 'data'

class CodeTestData(TypedDict):  # Renamed from ConfigTestData
    """Type definition for code test data"""
    path: Path
    source_path: Path  # Renamed from config_path
    source: str
    expected_classes: Dict[str, Dict[str, str]]

# Test data using source code files
TEST_DATA: Dict[str, CodeTestData] = {
    'mirror': {
        'path': TEST_DATA_ROOT / '@tc_mirrorform/addons/mirrorform.pbo',
        'source_path': TEST_DATA_ROOT / '@tc_mirrorform/addons/mirrorform/tc/mirrorform/config.cpp',
        'source': 'tc_mirrorform',
        'expected_classes': {
            # 'CfgPatches': {'parent': ''},
            # 'CfgWeapons': {'parent': ''},
            # 'CfgVehicles': {'parent': ''},
            'TC_MIRROR': {'parent': '', 'section': 'CfgPatches'},
            'UniformItem': {'parent': ''},
            'Uniform_Base': {'parent': ''},
            'TC_U_Mirror_Base': {'parent': 'Uniform_Base', 'section': 'CfgWeapons'},
            'TC_U_Mirror_1': {'parent': 'TC_U_Mirror_Base', 'section': 'CfgWeapons'},
            'B_Soldier_base_F': {'parent': ''},
            'TC_B_Mirror_Base': {'parent': 'B_Soldier_base_F', 'section': 'CfgVehicles'},
            'TC_B_Mirror_1': {'parent': 'TC_B_Mirror_Base', 'section': 'CfgVehicles'}
        }
    },
    'headband': {
        'path': TEST_DATA_ROOT / '@tc_rhs_headband/addons/rhs_headband.pbo',
        'source_path': TEST_DATA_ROOT / '@tc_rhs_headband/addons/rhs_headband/tc/rhs_headband/config.cpp',
        'source': 'tc_rhs_headband',
        'expected_classes': {
            'tc_rhs_headband': {'parent': 'rhs_headband'},
            'ItemCore': {'parent': ''},
            'H_HelmetB': {'parent': 'ItemCore'}
        }
    },
    'em_babe': {
        'path': TEST_DATA_ROOT / '@em/addons/babe_em.pbo',
        'source_path': TEST_DATA_ROOT / '@em/addons/babe_em/babe/babe_em/config.cpp',
        'source': 'em',
        'expected_classes': {
            'BaBe_EM': {'parent': ''},
            'babe_helper': {'parent': 'TargetGrenade'},
            'All': {'parent': ''},
            'Static': {'parent': 'All'},
            'Building': {'parent': 'Static'},
            'NonStrategic': {'parent': 'Building'},
            'TargetTraining': {'parent': 'NonStrategic'},
            'TargetGrenade': {'parent': 'TargetTraining'}
        }
    }
}

@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Configure logging for tests"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )

@pytest.fixture
def sample_configs() -> Dict[str, CodeTestData]:
    """Provide test config data"""
    return TEST_DATA

@pytest.fixture
def api():
    """Provide API instance"""
    return ClassAPI()

@pytest.fixture
def parser():
    """Provide ClassParser instance"""
    return ClassParser()

@pytest.fixture
def test_structure(tmp_path: Path) -> Path:
    """Create minimal test directory structure"""
    mod_dir = tmp_path / "@test_mod"
    mod_dir.mkdir()
    (mod_dir / "addons").mkdir()
    return tmp_path

__all__ = ['sample_configs', 'api', 'parser', 'test_structure', 'TEST_DATA_ROOT']