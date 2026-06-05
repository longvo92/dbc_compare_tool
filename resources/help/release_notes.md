# DBC Compare Tool - Release Notes

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

### Known Notes (v0.1.0)

- Review and update this release note before distributing the build.
- Update version fields in resources/version_info.txt when publishing a new version.

### Known Limitations

* Signal rename detection may not be fully reliable for Event Matrix messages that contain many boolean event signals with highly similar definitions.
* When multiple signals have identical technical properties and differ primarily by name, the comparison engine may not be able to determine whether a signal was renamed or replaced, resulting in Add/Remove classifications instead of Rename.
* This limitation does not affect detection of actual signal property changes.
