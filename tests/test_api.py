import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict
from src.models import ClassData, PboClasses
from api import API, Scanner


@pytest.fixture
def mock_pbo_classes():
    return PboClasses(
        classes={
            "Vehicle": ClassData(
                name="Vehicle",
                parent="Object",
                properties={"model": "vehicle.p3d"},
                source_file=Path("config.cpp")
            ),
            "Car": ClassData(
                name="Car",
                parent="Vehicle",
                properties={"maxSpeed": "200"},
                source_file=Path("config.cpp")
            )
        },
        source="test.pbo"
    )


@pytest.fixture
def api():
    """Create API instance for testing"""
    return API()

@pytest.fixture
def test_dir(tmp_path):
    """Create test directory with sample PBO files"""
    test_dir = tmp_path / "test_pbos"
    test_dir.mkdir()
    
    # Create valid PBO files with proper headers
    for i in range(1, 4):
        pbo_path = test_dir / f"test{i}.pbo"
        with open(pbo_path, 'wb') as f:
            f.write(b'\0sreV\0\0\0\0' + f'Test PBO {i}'.encode())
    
    # Create a non-PBO file
    (test_dir / "notapbo.txt").touch()
    
    return test_dir


def test_scan_directory_empty(api, tmp_path):
    """Test scanning empty directory"""
    results = api.scan_directory(tmp_path)
    assert len(results) == 0


def test_scan_directory_with_pbo(api, tmp_path, mock_pbo_classes):
    """Test scanning directory with PBO file"""
    # Create mock PBO file
    pbo_path = tmp_path / "test.pbo"
    pbo_path.touch()

    # Mock scanner to return test data
    with patch.object(api.scanner, 'scan_pbo', return_value=mock_pbo_classes):
        results = api.scan_directory(tmp_path)

    assert len(results) == 1
    assert str(pbo_path) in results
    assert len(results[str(pbo_path)].classes) == 2
    assert "Vehicle" in results[str(pbo_path)].classes
    assert "Car" in results[str(pbo_path)].classes


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


def test_clear_cache(api, tmp_path, mock_pbo_classes):
    """Test cache clearing"""
    pbo_path = tmp_path / "test.pbo"
    pbo_path.touch()

    with patch.object(api.scanner, 'scan_pbo', return_value=mock_pbo_classes) as mock_scan:
        # First scan
        api.scan_directory(tmp_path)
        assert mock_scan.call_count == 1

        # Clear cache
        api.clear_cache()

        # Should scan again after cache clear
        api.scan_directory(tmp_path)
        assert mock_scan.call_count == 2


def test_api_initialization(api):
    """Test API class initialization"""
    assert isinstance(api.scanner, Scanner)
    assert isinstance(api._cache, dict)
    assert api._progress_callback is None

def test_set_progress_callback(api):
    """Test setting progress callback"""
    def callback(msg): pass
    
    api.set_progress_callback(callback)
    assert api._progress_callback == callback

def test_clear_cache(api, test_dir):
    """Test cache clearing functionality"""
    # Populate cache
    api.scan_directory(test_dir)
    assert len(api._cache) > 0
    
    # Clear cache
    api.clear_cache()
    assert len(api._cache) == 0

def test_scan_directory_basic(api, test_dir):
    """Test basic directory scanning"""
    results = api.scan_directory(test_dir)
    
    assert len(results) == 3  # Should find 3 PBO files
    assert all(str(test_dir) in path for path in results.keys())
    assert all(isinstance(result, PboClasses) for result in results.values())

def test_scan_directory_with_limit(api, test_dir):
    """Test directory scanning with file limit"""
    results = api.scan_directory(test_dir, file_limit=2)
    assert len(results) == 2

def test_scan_directory_caching(api, test_dir):
    """Test that scanning caches results"""
    # First scan
    first_results = api.scan_directory(test_dir)
    cache_size = len(api._cache)
    
    # Second scan
    second_results = api.scan_directory(test_dir)
    
    assert len(api._cache) == cache_size
    assert first_results == second_results

def test_progress_callback_execution(api, test_dir):
    """Test progress callback is called correctly"""
    callback_calls = []
    def test_callback(msg):
        callback_calls.append(msg)
    
    api.set_progress_callback(test_callback)
    api.scan_directory(test_dir)
    
    assert len(callback_calls) == 3  # Should be called for each PBO
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

def test_cache_persistence(api, test_dir):
    """Test that cache persists between scans"""
    # First scan to populate cache
    api.scan_directory(test_dir)
    initial_cache = api._cache.copy()
    
    # Modify a file timestamp but keep cache
    test_pbo = next(test_dir.glob("*.pbo"))
    test_pbo.touch()
    
    # Second scan should use cached results
    results = api.scan_directory(test_dir)
    assert api._cache == initial_cache
    assert all(str(test_dir) in path for path in results.keys())

def test_partial_directory_scan(api, test_dir):
    """Test scanning directory with some files already cached"""
    # First scan only some files
    first_results = api.scan_directory(test_dir, file_limit=2)
    cached_files = set(api._cache.keys())
    
    # Second scan all files
    all_results = api.scan_directory(test_dir)
    
    # Verify cached results were reused
    assert all(path in all_results for path in cached_files)
    assert len(all_results) > len(first_results)

def test_scanner_none_result_handling(api, test_dir):
    """Test handling of None results from scanner"""
    class NoneScanner(Scanner):
        def scan_pbo(self, path):
            return None
    
    api.scanner = NoneScanner()
    results = api.scan_directory(test_dir)
    assert len(results) == 0
