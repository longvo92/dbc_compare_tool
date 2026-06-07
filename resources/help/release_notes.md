# DBC Compare Tool - Release Notes
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
