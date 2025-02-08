import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.models import ClassData, PboClasses


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
