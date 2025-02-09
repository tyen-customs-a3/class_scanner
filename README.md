# Class Scanner

A Python package for scanning and analyzing classes in game mod PBO files.

## Installation

For development:
```bash
git clone <repository-url>
cd class_scanner
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

## Usage

Basic example:
```python
from class_scanner import ClassScanner
from pathlib import Path

scanner = ClassScanner()
results = scanner.scan_directory(Path("path/to/mods"))

for pbo_path, pbo_data in results.items():
    print(f"\nClasses in {pbo_path}:")
    for name, class_data in pbo_data.classes.items():
        print(f"  {name} -> {class_data.parent}")
```

## Project Structure

```
class_scanner/
├── src/
│   └── class_scanner/
│       ├── __init__.py      # Package exports
│       ├── scanner.py       # Main scanning logic
│       ├── models/          # Data structures
│       ├── parser/          # Config parsing
│       └── pbo/            # PBO handling
├── tests/                  # Test suite
└── pyproject.toml         # Package configuration
```

## Core Components

### Models
- `ClassData`: Represents a single class definition
  - name: Class name
  - parent: Parent class name
  - properties: Class properties
  - source_file: Config file path

- `PboClasses`: Container for PBO scanning results
  - classes: Dictionary of ClassData objects
  - source: Source PBO path

### Scanners
- `ClassScanner`: Full-featured scanner with config parsing
- `Scanner`: Base scanner interface for custom implementations

## Development

1. Make changes
2. Run tests: `pytest`
3. Submit pull request

## Requirements

- Python 3.8+
- Access to mod directories