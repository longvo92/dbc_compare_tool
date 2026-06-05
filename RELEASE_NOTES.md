# Release Notes

## Version 0.1.0 (Initial Release)

### Overview

DBC Compare Tool is a desktop utility for automotive engineers to compare CAN DBC baseline folders and generate comprehensive Excel reports. This initial release provides a stable, feature-complete solution for identifying changes between DBC revisions.

### Features

#### Core Comparison Capabilities
- **Automatic DBC Discovery**: Recursively discovers all `.dbc` files in baseline folders
- **Intelligent File Pairing**: Uses CAN ID overlap and structural similarity to match renamed `.dbc` files
- **Change Detection**: Identifies added, removed, modified, and **renamed** messages and signals
- **Smart Rename Recognition**: Structural matching for messages (frame ID + layout) and signals (bit position + length)
- **Multiplexing Support**: Properly handles CAN multiplexing metadata and signal relationships
- **Extended Frame Support**: Detects and processes extended CAN frame IDs
- **Attribute Extraction**: Captures message cycle-time and other key DBC attributes

#### Report Generation
- **Excel Output**: Professional three-sheet workbook format
  - **Summary**: High-level overview of all changes
  - **Message Details**: Detailed message-level changes with CAN IDs and layouts
  - **Signal Details**: Signal-level changes including bit positions and attributes

#### User Interfaces
- **Desktop GUI** (PySide6): Intuitive folder selection, real-time processing with progress indicators
- **Command-Line Interface**: Automation-friendly for CI/CD integration and batch processing
- **Standalone Executable**: PyInstaller-packaged Windows binary for distribution without Python dependency

### Technical Highlights

- **Separation of Concerns**: Core comparison logic independent from UI, enabling testing and CLI reuse
- **Non-blocking UI**: Worker threads keep desktop interface responsive during large comparisons
- **Cantools Integration**: Leverages industry-standard CAN database parser for reliability
- **Deterministic Matching**: File pairing strategy prioritizes structural indicators over heuristics

### Supported Environments

- **Desktop GUI**: Windows 10 or later
- **CLI & Source**: Windows 10+ or any OS with Python 3.10+
- **Dependencies**: cantools ≥ 41.4.0, openpyxl ≥ 3.1.0, PySide6 ≥ 6.7.0

### Installation

**Option 1: Standalone Executable (Windows)**
```
Download: DBCCompareTool-0.1.0-x64.zip from releases
Extract and run: dbc_compare_tool.exe
```

**Option 2: From Source**
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m dbc_compare_tool          # GUI
.\.venv\Scripts\python.exe -m dbc_compare_tool.cli --old <path> --new <path> --out report.xlsx  # CLI
```

### Known Limitations & Future Enhancements

- Project-specific DBC attributes beyond cycle-time require custom configuration
- GUI limited to single comparison at a time (batch mode available via CLI)
- Excel report styling expandable in future versions
- Custom DBC attribute support planned for v0.2.0

### System Requirements

- **Desktop GUI**: Windows 10 or later
- **CLI & Development**: Windows/macOS/Linux with Python 3.10+
- **Minimum RAM**: 512 MB recommended
- **Disk Space**: ~100 MB for standalone executable

### Breaking Changes

None (initial release)

### Migration Guide

N/A (initial release)

### Contributors & Support

Report issues or request features on the project repository. For documentation, see:
- [Architecture Overview](docs/architecture.md)
- [User Guide](resources/help/user_guide.md)
- [README](README.md)
