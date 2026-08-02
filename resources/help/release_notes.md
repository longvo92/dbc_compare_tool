# DBC Compare Tool - Release Notes

## Version 0.2.0

### Added

- **Signal Focus tab**: a second comparison mode for application-layer work. Pick the ECU node your software runs on, optionally paste or import the list of signals it uses, and get a report about those signals only — data type, scaling, range, unit, value table, and init value. Frames, CAN IDs, DLC, cycle time, and bit positions are treated as transport details, so a signal that merely moved to another message is no longer reported as removed and added.
- **Per-value value-table comparison**: every changed `VAL_` entry is listed on its own, marked as relabeled, added, or removed. A raw value that kept its number but changed meaning is highlighted, since existing software keeps building against it silently.
- **Init value comparison**: `GenSigStartValue` is now read and compared.
- **Signal list import**: the application's signal list can be pasted directly or imported from a `.txt`/`.csv` file; comment lines and extra columns are ignored.

---
## Version 0.1.8

### Added

- **Manual DBC pairing**: a new **Manual Pairing…** dialog lets you pick the new-baseline file for each old-baseline file yourself, then **Save** the pairing. Unpaired old files are reported as removed; unselected new files as added. Manually matched pairs appear as **Manually Paired** on the DBC Overview sheet.
- **Separate run buttons**: **Run Auto Compare** pairs files automatically by relative path and content similarity (as before); **Run Manual Compare** uses your saved manual pairing (or automatic pairing if none is saved) and adds the signal-rename review step.
- **Review renamed signals before export**: after a manual-compare run finishes, a review dialog lists every auto-detected signal rename with its confidence. Uncheck a row to reject the rename — it is then exported as a **Removed + Added** pair instead. **Run Auto Compare** keeps the fully automatic behavior.

---
## Version 0.1.7

### Added

- New application icon, shown in the window title bar, taskbar, and on the `.exe` file.

### Changed

- Rewrote the **User Guide** with step-by-step usage instructions, a report sheet reference, and practical tips.
- Cleaned up these Release Notes to focus on what matters to users.

---
## Version 0.1.6

### Fixed

- **More accurate comparison**: a standard frame and an extended frame sharing the same numeric CAN ID are no longer confused with each other, so changes on both are reported correctly.
- **One corrupt DBC no longer stops the comparison**: unparsable files are marked **Parse Error** (highlighted red on the DBC Overview sheet) and the remaining files are still compared.
- **Encoding support**: DBC files with special characters (e.g. `°C`) or unusual encodings now open reliably instead of causing an error.
- **Safe exit**: closing the window while a comparison is running now asks for confirmation and shuts down cleanly instead of crashing.

### Added

- **Match reasons in the report**: renamed messages and signals now include a `Matched by: ...` line (e.g. `Start bit matched, Factor matched, Names are similar`) explaining why the pair was matched.

---
## Version 0.1.5

### Changed

- **Refreshed interface**: cleaner header with title and version badge, modern light theme with rounded panels and a dark console-style log area.

---
## Version 0.1.4

### Added

- **DBC Overview sheet**: one row per DBC file pair with pairing status (`Matched` / `DBC Added` / `DBC Removed` / `DBC Renamed`), pairing confidence, and message/signal counts for both baselines.
- **Remembered paths**: the tool now remembers the last-used Old Baseline, New Baseline, and Report Path across sessions.
- **Per-file progress**: the Execution Log shows each DBC file as it is processed (e.g. `[2/7] Comparing: Bus_A.dbc`).
- **Status bar**: shows `Ready` on startup, a change count summary after a successful run, and an error notice on failure.

### Changed

- **Resizable layout**: drag the divider between the input panel and the Execution Log to resize the log area.

---
## Version 0.1.3

### Added

- **Property Diff sheet**: before/after table for every changed property, one row per property. Old values highlighted in salmon, new values in green.
- **Change Type filter**: checkboxes (Added / Removed / Modified / Renamed) let you include only the change categories you care about.
- **Drag & drop**: drag a folder directly onto the Old Baseline or New Baseline fields instead of using the Browse button.

### Changed

- **CAN ID in hexadecimal** (`0x1A3`) across all report sheets, consistent with automotive toolchain conventions.
- **Report styling** overhauled for readability: rows color-coded by change type (green = Added, salmon = Removed, yellow = Modified, blue = Renamed), highlighted confidence levels, report title and timestamp on the Summary sheet.

---
## Version 0.1.2

### Changed

- **Improved rename detection** with confidence-based classification.
- New **Possible Rename** status for ambiguous cases, particularly Event Matrix messages containing many structurally similar signals — fewer false-positive renames.
- Cleaner, more readable comparison results.

---
## Version 0.1.1

### Changed

- Cleaner main window appearance and improved application icon.

---
## Version 0.1.0

First release.

### Added

- Folder-based DBC baseline comparison.
- Excel report with Summary, Message Details, and Signal Details sheets.
- Message and signal add/remove/modify/rename detection with detailed old → new property descriptions.
- Help menu with User Guide, Release Notes, and About pages.
