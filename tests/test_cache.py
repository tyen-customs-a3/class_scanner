import pytest
from pathlib import Path
import json

from class_scanner.cache import ClassCache
from class_scanner.models import PboScanData, ClassData, CacheFileStructure

@pytest.fixture
def sample_pbo_classes():
    """Create sample PBO classes for testing"""
    return PboScanData(
        classes={
            "TestClass": ClassData(
                name="TestClass",
                parent="ParentClass",
                properties={},
                source_file=Path("test.pbo"),
                container="CfgVehicles"
            )
        },
        source="test_addon"
    )

@pytest.fixture
def populated_cache(sample_pbo_classes):
    """Create a cache with sample data"""
    cache = ClassCache(max_cache_size=10)
    cache.add("test.pbo", sample_pbo_classes)
    return cache

def test_cache_save_and_load(populated_cache, sample_pbo_classes, tmp_path):
    """Test saving and loading cache from disk"""
    cache_file = tmp_path / "test_cache.json"
    
    # Save cache
    populated_cache.save_to_disk(cache_file)
    assert cache_file.exists()
    
    # Load cache
    loaded_cache = ClassCache.load_from_disk(cache_file)
    
    # Verify loaded data
    assert loaded_cache.max_cache_size == populated_cache.max_cache_size
    assert loaded_cache._last_updated.date() == populated_cache._last_updated.date()
    
    original = populated_cache.get("test.pbo")
    loaded = loaded_cache.get("test.pbo")
    assert original is not None and loaded is not None
    assert original.source == loaded.source
    assert list(original.classes.keys()) == list(loaded.classes.keys())

def test_cache_file_structure(populated_cache, tmp_path):
    """Test the structure of the saved cache file"""
    cache_file = tmp_path / "test_cache.json"
    populated_cache.save_to_disk(cache_file)
    
    with cache_file.open('r') as f:
        data = json.load(f)
    
    # Use CacheFileStructure keys for validation
    expected_keys = set(CacheFileStructure.__annotations__.keys())
    assert set(data.keys()) == expected_keys
    
    # Type validation
    assert isinstance(data['max_cache_size'], int)
    assert isinstance(data['last_updated'], str)
    assert isinstance(data['pbo_cache'], dict)
    assert isinstance(data['class_cache'], dict)
    
    # Validate PboScanData structure if cache has entries
    if data['pbo_cache']:
        pbo_entry = next(iter(data['pbo_cache'].values()))
        expected_pbo_keys = {'classes', 'source', 'last_accessed'}
        assert set(pbo_entry.keys()) == expected_pbo_keys

def test_cache_invalid_file(tmp_path):
    """Test loading from invalid cache file"""
    cache_file = tmp_path / "invalid_cache.json"
    cache_file.write_text("invalid json")
    
    with pytest.raises(Exception):
        ClassCache.load_from_disk(cache_file)

def test_cache_missing_file(tmp_path):
    """Test loading from non-existent file"""
    cache_file = tmp_path / "nonexistent.json"
    
    with pytest.raises(FileNotFoundError):
        ClassCache.load_from_disk(cache_file)

def test_cache_persistence_with_multiple_entries(tmp_path):
    """Test persistence with multiple cache entries"""
    cache = ClassCache(max_cache_size=10)
    cache_file = tmp_path / "multi_cache.json"
    
    # Add multiple entries
    for i in range(3):
        cache.add(
            f"test_{i}.pbo",
            PboScanData(
                classes={
                    f"Class_{i}": ClassData(
                        name=f"Class_{i}",
                        parent="Base",
                        properties={},
                        source_file=Path(f"test_{i}.pbo")
                    )
                },
                source=f"addon_{i}"
            )
        )
    
    # Save and reload
    cache.save_to_disk(cache_file)
    loaded_cache = ClassCache.load_from_disk(cache_file)
    
    # Verify all entries were preserved
    assert len(loaded_cache._pbo_cache) == 3
    for i in range(3):
        assert loaded_cache.get(f"test_{i}.pbo") is not None

def test_cache_max_size_preservation(tmp_path):
    """Test that max cache size is preserved after load"""
    custom_size = 42
    cache = ClassCache(max_cache_size=custom_size)
    cache_file = tmp_path / "sized_cache.json"
    
    cache.save_to_disk(cache_file)
    loaded_cache = ClassCache.load_from_disk(cache_file)
    
    assert loaded_cache.max_cache_size == custom_size
