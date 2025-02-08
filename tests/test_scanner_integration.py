import pytest
from pathlib import Path
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scanner import ClassScanner
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

def test_malformed_class_definition(scanner: ClassScanner, tmp_path: Path):
    """Test handling of malformed class definitions"""
    pbo_dir = tmp_path / "test_malformed"
    pbo_dir.mkdir()
    config_file = pbo_dir / "config.cpp"
    
    # Write malformed class definition
    config_file.write_text("""
    class Bad1 {  // Missing parent
        class Bad2 : {  // Invalid parent syntax
        class Bad3 : Good {  // Missing closing brace
        class Bad4 : Good };  // Extra semicolon
        class {};  // Empty class name
    """)
    
    result = scanner.scan_directory(pbo_dir)
    assert not result or all('Bad' not in str(classes) 
                           for classes in result.values())

def test_empty_and_whitespace_files(scanner: ClassScanner, tmp_path: Path):
    """Test handling of empty and whitespace-only files"""
    pbo_dir = tmp_path / "test_empty"
    pbo_dir.mkdir()
    
    # Create empty file
    (pbo_dir / "empty.cpp").touch()
    
    # Create whitespace-only file
    (pbo_dir / "whitespace.cpp").write_text("\n\n  \t  \n")
    
    result = scanner.scan_directory(pbo_dir)
    assert not result, "Expected no results from empty files"

def test_large_file_handling(scanner: ClassScanner, tmp_path: Path):
    """Test handling of large files"""
    pbo_dir = tmp_path / "test_large"
    pbo_dir.mkdir()
    
    # Create large file with repeated class definitions
    large_content = "class Test{};\\n" * 100000
    (pbo_dir / "large.cpp").write_text(large_content)
    
    result = scanner.scan_directory(pbo_dir)
    assert result is not None, "Scanner should handle large files"

def test_special_characters_in_names(scanner: ClassScanner, tmp_path: Path):
    """Test handling of special characters in class names"""
    pbo_dir = tmp_path / "test_special"
    pbo_dir.mkdir()
    
    special_classes = """
    class Test-Name {};
    class Test@Name {};
    class Test#Name {};
    class Test$Name {};
    class Test&Name {};
    class Test.Name {};
    """
    
    (pbo_dir / "special.cpp").write_text(special_classes)
    result = scanner.scan_directory(pbo_dir)
    assert result is not None, "Scanner should handle special characters"

def test_circular_inheritance(scanner: ClassScanner, tmp_path: Path):
    """Test handling of circular class inheritance"""
    pbo_dir = tmp_path / "test_circular"
    pbo_dir.mkdir()
    
    circular_classes = """
    class A : C {};
    class B : A {};
    class C : B {};
    """
    
    (pbo_dir / "circular.cpp").write_text(circular_classes)
    result = scanner.scan_directory(pbo_dir)
    assert result is not None, "Scanner should handle circular inheritance"

def test_deeply_nested_classes(scanner: ClassScanner, tmp_path: Path):
    """Test handling of deeply nested class definitions"""
    pbo_dir = tmp_path / "test_nested"
    pbo_dir.mkdir()
    
    # Create deeply nested class structure
    nested_content = "class" + "{ class".join([f"Level{i}" for i in range(50)]) + "{};" * 50
    
    (pbo_dir / "nested.cpp").write_text(nested_content)
    result = scanner.scan_directory(pbo_dir)
    assert result is not None, "Scanner should handle deeply nested classes"

def test_mixed_line_endings(scanner: ClassScanner, tmp_path: Path):
    """Test handling of mixed line endings"""
    pbo_dir = tmp_path / "test_endings"
    pbo_dir.mkdir()
    
    content = "class Unix {}\n" + "class Windows {}\r\n" + "class Mac {}\r"
    (pbo_dir / "endings.cpp").write_text(content)
    
    result = scanner.scan_directory(pbo_dir)
    assert result is not None
    if result:
        first_result = next(iter(result.values()))
        assert len(first_result.classes) == 3, "Should find all classes regardless of line endings"

def test_unicode_characters(scanner: ClassScanner, tmp_path: Path):
    """Test handling of Unicode characters in class definitions"""
    pbo_dir = tmp_path / "test_unicode"
    pbo_dir.mkdir()
    
    unicode_content = """
    class TestÜnicode {};
    class TestЮникод {};
    class Test数字 {};
    """
    
    (pbo_dir / "unicode.cpp").write_text(unicode_content, encoding='utf-8')
    result = scanner.scan_directory(pbo_dir)
    assert result is not None, "Scanner should handle Unicode characters"
