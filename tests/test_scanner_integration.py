import pytest
from pathlib import Path
from scanner import ClassScanner
from .conftest import TEST_DATA

@pytest.fixture
def sample_data_path() -> Path:
    """Get path to sample data directory"""
    return Path('sample_data')

@pytest.fixture
def scanner() -> ClassScanner:
    """Create scanner instance"""
    return ClassScanner()

def test_scan_sample_directory(scanner: ClassScanner, sample_configs):
    """Test scanning sample data directory structure"""
    root_path = sample_configs['mirror']['path'].parent.parent.parent
    assert root_path.exists(), "Sample data directory not found"
    
    # Scan directory
    results = scanner.scan_directory(root_path)
    
    # Check if any results were found
    assert results, "No results found"


def test_pbo_content_extraction(scanner: ClassScanner, sample_configs):
    """Test extraction of PBO contents"""
    mirror_data = sample_configs['mirror']
    pbo_path = mirror_data['path']
    assert pbo_path.exists(), "Test PBO not found"
    
    # Scan single PBO
    result = scanner.scan_pbo(pbo_path)
    assert result is not None
    
    # Verify basic class structure matches expected data
    for class_name, class_info in mirror_data['expected_classes'].items():
        assert class_name in result.classes, f"Missing class: {class_name}"
        if class_info['parent']:
            assert result.classes[class_name].parent == class_info['parent'], \
                f"Wrong parent for {class_name}"

def test_scan_multiple_pbos(scanner: ClassScanner, sample_configs):
    """Test scanning multiple PBO files"""
    for config_name, config_data in sample_configs.items():
        pbo_path = config_data['path']
        assert pbo_path.exists(), f"PBO not found: {config_name}"
        
        result = scanner.scan_pbo(pbo_path)
        assert result is not None
        
        print (result.classes)
        
        # Verify expected classes are present
        for class_name in config_data['expected_classes']:
            assert class_name in result.classes, \
                f"Missing class {class_name} in {config_name}"

def test_scan_invalid_directory(scanner: ClassScanner, tmp_path: Path):
    """Test scanner behavior with invalid directory"""
    invalid_dir = tmp_path / "nonexistent"
    results = scanner.scan_directory(invalid_dir)
    assert not results, "Expected empty results for invalid directory"

def test_scan_empty_directory(scanner: ClassScanner, tmp_path: Path):
    """Test scanner behavior with empty directory"""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    results = scanner.scan_directory(empty_dir)
    assert not results, "Expected empty results for directory without PBOs"
