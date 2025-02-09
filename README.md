# Class Scanner

A Python package for scanning game mod classes.

## Installation

To install directly from the repository:

```bash
pip install git+https://github.com/yourusername/class_scanner.git
```

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment
4. Install development dependencies: `pip install -e ".[dev]"`

## Features

- Scan PBO files for class definitions
- Parse class inheritance hierarchies
- Handle nested class structures
- Support multiple config sections (CfgPatches, CfgWeapons, CfgVehicles, etc.)
- Extract and convert binary config files
- Smart file encoding detection
- Progress tracking for batch operations
- Basic caching system

## Requirements

- Python 3.9+
- extractpbo tool in system PATH
- Read permissions for target directories

## Architecture

### Core Components

- **ClassParser**: Handles raw config.cpp parsing
  - Class definition extraction
  - Inheritance tracking
  - Section organization (CfgPatches, CfgWeapons, etc.)

- **PboExtractor**: Manages PBO archive operations
  - PBO extraction using extractpbo
  - Binary file conversion
  - Multi-encoding support
  - Temporary file management

- **API**: High-level interface providing
  - Directory scanning
  - Cache management
  - Progress reporting
  - File limiting

### Data Model

- **ClassData**: Core class representation
  ```python
  class ClassData:
      name: str                # Class name
      parent: str             # Parent class name (empty string if none)
      properties: Dict        # Class properties
      source_file: Path      # Source config file
  ```

- **PboClasses**: Container for classes from a PBO
  ```python
  class PboClasses:
      classes: Dict[str, ClassData]  # Class definitions
      source: str                    # Source PBO path
  ```

## Usage

Basic scanning example:
```python
from scanner import ClassScanner
from pathlib import Path

scanner = ClassScanner()
results = scanner.scan_directory(Path("mods/@your_mod"))

# Access class data
for pbo_path, pbo_classes in results.items():
    for class_name, class_data in pbo_classes.classes.items():
        print(f"Found class {class_name} with parent {class_data.parent}")
```

## Contributing
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with tests

## License
MIT License