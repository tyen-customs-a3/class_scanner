import pytest
import logging
from pathlib import Path
from typing import Dict, TypedDict
from api import API
from parser import ClassParser

# Core test configuration 
ROOT_DIR = Path(__file__).parent.parent
TEST_DATA_ROOT = ROOT_DIR / 'tests' / 'data'

class ConfigTestData(TypedDict):
    """Type definition for config test data"""
    path: Path
    config_path: Path
    source: str
    expected_classes: Dict[str, Dict[str, str]]

# Test data using config.cpp files
TEST_DATA: Dict[str, ConfigTestData] = {
    'mirror': {
        'path': TEST_DATA_ROOT / '@tc_mirrorform/addons/mirrorform.pbo',
        'config_path': TEST_DATA_ROOT / '@tc_mirrorform/addons/mirrorform/tc/mirrorform/config.cpp',
        'source': 'tc_mirrorform',
        'expected_classes': {
            'TC_MIRROR': {'parent': ''},
            'TC_U_Mirror_Base': {'parent': 'Uniform_Base'},
            'TC_U_Mirror_1': {'parent': 'TC_U_Mirror_Base'},
            'TC_B_Mirror_Base': {'parent': 'B_Soldier_base_F'},
            'TC_B_Mirror_1': {'parent': 'TC_B_Mirror_Base'}
        }
    },
    'headband': {
        'path': TEST_DATA_ROOT / '@tc_rhs_headband/addons/rhs_headband.pbo',
        'config_path': TEST_DATA_ROOT / '@tc_rhs_headband/addons/rhs_headband/tc/rhs_headband/config.cpp',
        'source': 'tc_rhs_headband',
        'expected_classes': {
            'tc_rhs_headband': {'parent': 'rhs_headband'},
            'ItemCore': {'parent': ''},
            'H_HelmetB': {'parent': 'ItemCore'}
        }
    },
    'em_babe': {
        'path': TEST_DATA_ROOT / '@em/addons/babe_em.pbo',
        'config_path': TEST_DATA_ROOT / '@em/addons/babe_em/babe/babe_em/config.cpp',
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
def sample_configs() -> Dict[str, ConfigTestData]:
    """Provide test config data"""
    return TEST_DATA

@pytest.fixture
def api():
    """Provide API instance"""
    return API()

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