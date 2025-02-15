import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from class_scanner.api import ClassAPI
from class_scanner.cache import ClassCache
from class_scanner.models import ClassData, PboScanData
from class_scanner.scanner import Scanner
from tests.conftest import TEST_DATA_ROOT

@pytest.fixture
def mock_pbo_classes(sample_configs):
    """Create PboClasses based on mirror test data"""
    mirror_data = sample_configs['mirror']
    classes = {
        name: ClassData(
            name=name,
            parent=data.get('parent', ''),
            properties={},  # Simplified properties for test
            source_file=mirror_data['source_path'],
            container=data.get('section', '')
        )
        for name, data in mirror_data['expected_classes'].items()
    }
    return PboScanData(classes=classes, source=mirror_data['source'])

@pytest.fixture
def api():
    """Create API instance for testing"""
    return ClassAPI()

@pytest.fixture
def test_dir(tmp_path, sample_configs):
    """Use the actual test data directory"""
    return TEST_DATA_ROOT


def test_scan_directory_empty(api, tmp_path):
    """Test scanning empty directory"""
    results = api.scan_directory(tmp_path)
    assert len(results) == 0


def test_scan_directory_with_pbo(api, test_dir, mock_pbo_classes):
    """Test scanning directory with PBO file"""
    results = api.scan_directory(test_dir)
    assert len(results) > 0
    # At least one of the test PBOs should be present
    test_paths = [TEST_DATA_ROOT / '@tc_mirrorform/addons/mirrorform.pbo',
                 TEST_DATA_ROOT / '@tc_rhs_headband/addons/rhs_headband.pbo',
                 TEST_DATA_ROOT / '@em/addons/babe_em.pbo']
    assert any(str(path) in results for path in test_paths)


def test_cache_functionality(api, tmp_path, mock_pbo_classes):
    """Test cache storage and retrieval"""
    pbo_path = tmp_path / "test.pbo"
    pbo_path.touch()

    # Mock scanner and verify it's called first time
    with patch.object(api.scanner, 'scan_pbo', return_value=mock_pbo_classes) as mock_scan:
        api.scan_directory(tmp_path)
        assert mock_scan.call_count == 1

        # Second scan should use cache
        api.scan_directory(tmp_path)
        assert mock_scan.call_count == 1


def test_progress_callback(api, tmp_path):
    """Test progress callback functionality"""
    # Create test files
    (tmp_path / "test1.pbo").touch()
    (tmp_path / "test2.pbo").touch()

    # Setup mock callback
    mock_callback = Mock()
    api.set_progress_callback(mock_callback)

    # Mock scanner to avoid actual scanning
    with patch.object(api.scanner, 'scan_pbo', return_value=None):
        api.scan_directory(tmp_path)

    assert mock_callback.call_count == 2
    assert all(str(tmp_path) in call.args[0] for call in mock_callback.call_args_list)


def test_file_limit(api, tmp_path, mock_pbo_classes):
    """Test file limit functionality"""
    # Create multiple test files
    for i in range(3):
        (tmp_path / f"test{i}.pbo").touch()

    with patch.object(api.scanner, 'scan_pbo', return_value=mock_pbo_classes):
        results = api.scan_directory(tmp_path, file_limit=2)

    assert len(results) == 2


def test_api_initialization(api):
    """Test API class initialization"""
    assert isinstance(api.scanner, Scanner)
    assert isinstance(api.cache, ClassCache)
    assert api._progress_callback is None

def test_set_progress_callback(api):
    """Test setting progress callback"""
    def callback(msg): pass
    
    api.set_progress_callback(callback)
    assert api._progress_callback == callback

def test_scan_directory_with_limit(api, test_dir):
    """Test directory scanning with file limit"""
    results = api.scan_directory(test_dir, file_limit=1)
    assert len(results) <= 1

def test_progress_callback_execution(api, test_dir):
    """Test progress callback is called correctly"""
    callback_calls = []
    def test_callback(msg):
        callback_calls.append(msg)
    
    api.set_progress_callback(test_callback)
    api.scan_directory(test_dir)
    
    assert len(callback_calls) > 0
    assert all('.pbo' in call for call in callback_calls)

def test_scan_nonexistent_directory(api):
    """Test scanning nonexistent directory"""
    results = api.scan_directory(Path("/nonexistent/path"))
    assert len(results) == 0

def test_scan_empty_directory(api, tmp_path):
    """Test scanning empty directory"""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    results = api.scan_directory(empty_dir)
    assert len(results) == 0

def test_scanner_none_result_handling(api, test_dir):
    """Test handling of None results from scanner"""
    class NoneScanner(Scanner):
        def scan_pbo(self, path):
            return None
    
    original_scanner = api.scanner
    api.scanner = NoneScanner()
    results = api.scan_directory(test_dir)
    api.scanner = original_scanner  # Restore original scanner
    assert len(results) == 0

def test_scan_single_pbo(api, test_dir, sample_configs):
    """Test scanning a single PBO file"""
    mirror_data = sample_configs['mirror']
    pbo_path = mirror_data['path']  # Use the complete path directly
    result = api.scan(pbo_path)
    
    assert result is not None
    assert isinstance(result, PboScanData)
    assert len(result.classes) > 0

def test_scan_nonexistent_pbo(api, tmp_path):
    """Test scanning a nonexistent PBO file"""
    nonexistent = tmp_path / "nonexistent.pbo"
    result = api.scan(nonexistent)
    assert result is None

def test_scan_invalid_file(api, tmp_path):
    """Test scanning an invalid file"""
    # Create invalid file
    invalid = tmp_path / "invalid.pbo"
    invalid.write_text("not a valid pbo")
    
    result = api.scan(invalid)
    assert result is None

def test_api_cache_persistence(api, test_dir, tmp_path):
    """Test API cache persistence between instances"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    # First API instance
    api1 = ClassAPI(cache_dir=cache_dir)
    results1 = api1.scan_directory(test_dir)
    assert len(results1) > 0
    
    # Second API instance should load from cache
    api2 = ClassAPI(cache_dir=cache_dir)
    results2 = api2.scan_directory(test_dir)
    
    # Results should match
    assert results1.keys() == results2.keys()
    for key in results1:
        assert results1[key].source == results2[key].source
        assert results1[key].classes.keys() == results2[key].classes.keys()
