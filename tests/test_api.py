import pytest
from pathlib import Path
import logging
import shutil
from tempfile import TemporaryDirectory

from class_scanner.cache import CacheConfig
try:
    from class_scanner import ClassAPI, ClassAPIConfig
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from class_scanner import ClassAPI, ClassAPIConfig
from .test_data import CLASS_TEST_DATA, PBO_PATHS, SAMPLE_DATA_ROOT

logger = logging.getLogger(__name__)

# Test Fixtures
@pytest.fixture
def api():
    """Create API instance for testing"""
    config = ClassAPIConfig(
        cache_config=CacheConfig(max_age=3600)
    )
    return ClassAPI(config)

@pytest.fixture
def sample_data_path() -> Path:
    """Fixture providing path to sample data directory"""
    return SAMPLE_DATA_ROOT

@pytest.fixture
def complex_class_code():
    """Get complex test class definitions"""
    return CLASS_TEST_DATA

# Test Categories
class TestAPIConfiguration:
    def test_default_config(self):
        """Test API initialization with default config"""
        api = ClassAPI()
        assert api.config.cache_max_age == 3600
        assert api.config.scan_timeout == 30

    def test_custom_config(self):
        """Test API initialization with custom config"""
        config = ClassAPIConfig(
            cache_max_age=7200,
            scan_timeout=60
        )
        api = ClassAPI(config)
        assert api.config.cache_max_age == 7200
        assert api.config.scan_timeout == 60
        assert api.config.cache_config.max_age == 7200  # Verify cache config is updated

class TestCacheOperations:
    def test_cache_add_get(self, api, complex_class_code, tmp_path):
        """Test adding and retrieving from cache"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(complex_class_code)
        
        # Use scan_file explicitly for non-PBO files
        hierarchy = api.scan_file(test_file)
        assert hierarchy is not None
        
        cached = api.get_cached_hierarchy(str(test_file))
        assert cached is not None
        assert cached.classes == hierarchy.classes

    def test_cache_clear(self, api, complex_class_code, tmp_path):
        """Test cache clearing"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(complex_class_code)
        
        api.scan_pbo(test_file)
        api.clear_cache()
        assert api.get_cached_hierarchy(str(test_file)) is None

class TestClassFinding:
    def test_find_by_name(self, api, complex_class_code, tmp_path):
        """Test finding classes by name"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(complex_class_code)
        api.scan_pbo(test_file)
        
        # Test with ObjectBase which we know exists in the test data
        results = api.find_class("ObjectBase")
        assert len(results) == 1
        hierarchy = next(iter(results.values()))
        assert "ObjectBase" in hierarchy.classes
        # Verify expected properties
        class_info = hierarchy.classes["ObjectBase"]
        assert class_info.properties["scope"] == "0"
        assert class_info.properties["model"] == ""

    def test_find_by_parent(self, api, complex_class_code, tmp_path):
        """Test finding classes by parent"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(complex_class_code)
        api.scan_pbo(test_file)
        
        children = api.find_classes_with_parent("ObjectBase")
        assert len(children) == 1
        assert "ItemBase" in next(iter(children.values()))

    def test_find_by_property(self, api, complex_class_code, tmp_path):
        """Test finding classes by property"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(complex_class_code)
        api.scan_pbo(test_file)
        
        with_scope = api.find_classes_with_property("scope")
        assert len(with_scope) == 1
        classes = next(iter(with_scope.values()))
        assert "ObjectBase" in classes
        assert "ItemBase" in classes

class TestPBOProcessing:
    """PBO file processing tests"""
    
    def test_pbo_inheritance(self, api, sample_data_path):
        """Test inheritance chains from PBOs"""
        found_inheritance = False
        
        for pbo_path in PBO_PATHS.values():
            if not pbo_path.exists():
                continue
                
            hierarchy = api.scan_pbo(pbo_path)
            if not hierarchy:
                continue
                
            # Look for inheritance chains
            for class_info in hierarchy.classes.values():
                if class_info.parent and class_info.inherited_properties:
                    found_inheritance = True
                    logger.info(f"Found inheritance: {class_info.name} -> {class_info.parent}")
                    logger.info(f"Inherited properties: {list(class_info.inherited_properties.keys())}")
                    break
                    
            if found_inheritance:
                break
                
        if not found_inheritance:
            pytest.skip("No inheritance chains found in PBOs")

    def test_nested_classes(self, api, sample_data_path):
        """Test nested class handling"""
        found_nested = False
        
        for pbo_path in PBO_PATHS.values():
            if not pbo_path.exists():
                continue
                
            hierarchy = api.scan_pbo(pbo_path)
            if not hierarchy:
                continue
                
            # Look for classes with nested structures
            for class_info in hierarchy.classes.values():
                nested_classes = {
                    name: props for name, props in class_info.properties.items()
                    if isinstance(props, dict) and 'type' in props
                }
                if nested_classes:
                    found_nested = True
                    logger.info(f"Found nested classes in {class_info.name}:")
                    for nested_name in nested_classes:
                        logger.info(f"  - {nested_name}")
                    break
                    
            if found_nested:
                break
                
        if not found_nested:
            pytest.skip("No PBO files with nested classes found")

class TestSpecialTypes:
    """Tests for special class types and properties"""
    
    def test_enum_definitions(self, api, complex_class_code, tmp_path):
        """Test enum parsing"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(complex_class_code)
        hierarchy = api.scan_pbo(test_file)
        
        assert "DamageType" in hierarchy.classes
        assert hierarchy.classes["DamageType"].type == "enum"
        assert hierarchy.classes["DamageType"].properties["KINETIC"] == "1"

    def test_array_properties(self, api, complex_class_code, tmp_path):
        """Test array property parsing"""
        test_file = tmp_path / "test.cpp"
        test_file.write_text(complex_class_code)
        hierarchy = api.scan_pbo(test_file)
        
        container = hierarchy.classes["Container"]
        assert "items" in container.properties
        assert "Item1" in container.properties["items"]

class TestErrorHandling:
    """Error handling tests"""
    
    def test_missing_pbo(self, api):
        """Test handling of missing PBO file"""
        result = api.scan_pbo(Path("nonexistent.pbo"))
        assert result is None

    def test_invalid_class_definition(self, api, tmp_path):
        """Test handling of invalid class definitions"""
        test_file = tmp_path / "invalid.cpp"
        # Use a more obviously invalid class definition
        test_file.write_text("""
            class {
                invalid syntax
            }
        """)
        
        hierarchy = api.scan_pbo(test_file)
        # Check that either we got None or the class was marked as invalid
        assert (hierarchy is None or 
                not hierarchy.classes or 
                len(hierarchy.invalid_classes) > 0)

class TestContextManager:
    def test_context_manager(self):
        """Test API context manager functionality"""
        with ClassAPI() as api:
            assert api is not None
            # Use API...
        # Should cleanup after exit

class TestRecursiveScanning:
    def test_recursive_scan(self, api, sample_data_path):
        """Test recursive scanning of sample data directory"""
        result = api.scan_directory(sample_data_path)
        assert result.success
        assert result.total_classes > 0
        
        # Verify we found expected classes from actual PBO content
        all_classes = set()
        for hierarchy in result.hierarchies.values():
            all_classes.update(hierarchy.classes.keys())
            
        # Log found classes for debugging
        logger.info(f"Found classes: {sorted(all_classes)}")
            
        # Test for classes we know exist in the sample PBOs
        assert "CfgModSettings" in all_classes  # Common config class
        assert "BABE_EM_FAT" in all_classes     # From babe_em.pbo
        
        # Check total class count
        assert len(all_classes) > 5  # We should have multiple classes

    def test_scan_with_nested_directories(self, api, sample_data_path):
        """Test scanning handles nested directory structure"""
        # Create nested structure in temp directory
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested directories
            mod_dir = temp_path / "@test_mod"
            addons_dir = mod_dir / "addons"
            addons_dir.mkdir(parents=True)
            
            # Copy sample PBOs to nested structure
            for pbo_path in sample_data_path.rglob("*.pbo"):
                shutil.copy2(pbo_path, addons_dir)
            
            # Scan nested structure
            result = api.scan_directory(temp_path)
            assert result.success
            assert result.total_classes > 0

    def test_scan_statistics(self, api, sample_data_path):
        """Test scan statistics are collected correctly"""
        result = api.scan_directory(sample_data_path)
        
        assert hasattr(result, 'scan_time')
        assert isinstance(result.total_classes, int)
        assert result.total_classes > 0
        
        # Check processed files count
        processed_count = sum(1 for _ in sample_data_path.rglob("*.pbo"))
        assert len(result.hierarchies) <= processed_count

    def test_cache_during_recursive_scan(self, api, sample_data_path):
        """Test cache behavior during recursive scanning"""
        # First scan
        result1 = api.scan_directory(sample_data_path)
        
        # Get cache state
        cached_hierarchies = api.get_cached_hierarchies()
        assert cached_hierarchies
        assert len(cached_hierarchies) == len(result1.hierarchies)
        
        # Second scan should use cache
        result2 = api.scan_directory(sample_data_path)
        assert result2.hierarchies == result1.hierarchies

@pytest.fixture
def sample_data_generator(tmp_path):
    """Create sample data structure for testing"""
    def _create_sample(class_data: str, filename: str = "test.cpp"):
        file_path = tmp_path / filename
        file_path.write_text(class_data)
        return file_path
    return _create_sample

class TestSampleData:
    def test_sample_data_exists(self, sample_data_path):
        """Verify sample data directory exists and contains PBOs"""
        assert sample_data_path.exists()
        assert any(sample_data_path.rglob("*.pbo"))

    def test_sample_data_content(self, api, sample_data_path):
        """Verify sample data contains expected content"""
        pbo_files = list(sample_data_path.rglob("*.pbo"))
        assert pbo_files
        
        # Test first PBO
        hierarchy = api.scan_pbo(pbo_files[0])
        assert hierarchy
        assert hierarchy.classes
