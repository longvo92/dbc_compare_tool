# DBC Compare Tool - Release Notes
## Version 0.1.3

### Added

- **Property Diff sheet** (4th Excel sheet): displays a structured before/after table for every changed property, one row per property. Old values are highlighted in salmon, new values in green for quick visual scanning.
- **Change Type filter** in the GUI: checkboxes (Added / Removed / Modified / Renamed) let users include only the change categories they care about before generating the report.
- **Drag & drop support** for folder inputs: users can now drag a folder directly onto the Old Baseline or New Baseline fields instead of using the Browse button.

### Changed

- **CAN ID** is now displayed in hexadecimal format (`0x1A3`) across all report sheets, consistent with automotive toolchain conventions.
- **Excel report styling** overhauled for readability:
  - Rows are color-coded by change type (green = Added, salmon = Removed, yellow = Modified, blue = Renamed).
  - Confidence Level cells are highlighted (green = High, yellow = Medium, red = Low) and bold.
  - Summary sheet now includes a report title and generation timestamp.
  - All cells have a subtle border grid and consistent row heights.

---
## Version 0.1.2

### Changed

* Improved rename detection by introducing confidence-based classification.
* Added **Possible Rename** status for cases where rename detection is ambiguous, particularly for Event Matrix messages containing many structurally similar signals.
* Reduced false-positive rename classifications by applying more conservative matching logic.
* Simplified report output by removing detailed **Rename Evidence** descriptions.
* Cleaned and streamlined comparison results for improved readability.
---
## Version 0.1.1

### Changed

- Removed author name from main window UI for cleaner appearance.
- Enhanced application icon handling with better resolution VinFast logo.

---

## Version 0.1.0

Draft release.

### Added

- Folder-based DBC baseline comparison.
- Excel report with Summary, Message Details, and Signal Details sheets.
- Message and signal add/remove/modify/rename detection.
- Detailed old -> new property descriptions.
- Rename rows also show changed properties, so rename plus min/max/factor/layout changes are not hidden.
- VinFast logo in the application and executable icon.
- Executable version metadata.
- Help menu with User Guide, Release Notes, and About pages.

---
### Known Limitations
- TBD
