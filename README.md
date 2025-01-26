# Class Scanner

A specialized Python tool for scanning and analyzing class definitions in game mod files, with support for PBO archives, inheritance tracking, and smart caching.

## Installation

## Features

- Multi-threaded scanning of class definitions
- PBO archive extraction and analysis
- Smart caching with thread-safe operations
- Inheritance chain tracking and validation
- Property analysis across class hierarchies
- Support for nested class structures
- Progress tracking during scans
- Source-based class organization

## Requirements

- Python 3.9+
- extractpbo tool in system PATH (for PBO file support)
- Read permissions for target directories

## Architecture

### Core Components

- **ClassParser**: Parses raw class definitions with support for:
  - Nested class structures
  - Enum definitions
  - Array properties
  - Property inheritance
  - PBO prefix handling

- **ClassScanner**: Handles file processing with:
  - Multi-threaded PBO extraction
  - Smart encoding detection
  - Progress tracking
  - Source tracking
  - Error handling

- **ClassAPI**: High-level interface providing:
  - Thread-safe caching
  - Batch operations
  - Validation
  - Search capabilities
  - Progress monitoring

### Data Model

- **ClassInfo**: Core class representation
  ```python
  class ClassInfo:
      name: str                       # Class name
      parent: Optional[str]           # Parent class name
      properties: Dict[str, str]      # Direct properties
      inherited_properties: Dict      # Properties from parent
      children: Set[str]             # Direct child classes
      file_path: Path                # Source file
      source: str                    # Origin PBO/file
      type: str                      # 'class' or 'enum'
  ```

- **ClassHierarchy**: Inheritance tree representation
  ```python
  class ClassHierarchy:
      classes: Dict[str, ClassInfo]   # All classes
      root_classes: Set[str]          # Classes without parents
      source: str                     # Source identifier
      invalid_classes: Set[str]       # Classes with errors
  ```

### Caching System

- Thread-safe class hierarchy caching
- Immutable cache containers
- Configurable cache age and size
- Smart cache invalidation
- Cache hit statistics

### Validation System

- Parent class validation
- Property inheritance verification
- Duplicate detection
- Cycle detection
- Similar class suggestions

### Processing Pipeline 

1. **Scan Phase**
   - Find PBO/code files
   - Extract content
   - Parse class definitions
   - Track source information

2. **Analysis Phase**  
   - Build inheritance trees
   - Validate relationships
   - Detect cycles
   - Resolve properties

3. **Cache Phase**
   - Store processed hierarchies
   - Track timestamps
   - Handle invalidation
   - Provide lookups

## Advanced Usage

### Custom Validation

## Command-Line Usage

### Basic Scanning Script

## Usage Examples

## Contributing
1. Fork the repository on GitHub.
2. Create a feature branch for your changes.
3. Submit a pull request once tests pass.

## License
This project is licensed under the MIT License.
