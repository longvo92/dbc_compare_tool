# DBC Compare Tool

Desktop utility for comparing Automotive CAN DBC baseline folders and generating an engineering-grade Excel report.

## What It Does

- Select an old baseline folder and a new baseline folder.
- Automatically discovers all `.dbc` files.
- Detects added, removed, modified, and renamed messages, including messages whose CAN ID changed.
- Detects added, removed, modified, and renamed signals, including when the `.dbc` file itself was renamed.
- Compares value tables (`VAL_`) and comments/descriptions (`CM_`) for both messages and signals.
- Generates one Excel workbook with five sheets:
  - `Summary`
  - `DBC Overview`
  - `Message Details`
  - `Signal Details`
  - `Property Diff`

Rename detection uses structural matching first. Name similarity is only supporting evidence. Files with different
relative paths are paired by CAN ID and message-layout overlap before message and signal comparison runs.

## Architecture

- `parser`: Cantools-backed DBC parser for messages, signals, multiplexing metadata, extended IDs, value tables, comments, and selected attributes.
- `comparator`: Folder and database comparison orchestration.
- `rename`: Pluggable rename detector interfaces and structural detectors.
- `report`: Excel report generation.
- `ui`: PySide6 desktop application.
- `cli`: Command-line entry point for automation and testing.

The comparison logic is independent from the UI.

## Development

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Run the GUI:

```powershell
.\.venv\Scripts\python.exe -m dbc_compare_tool
```

Run from CLI:

```powershell
.\.venv\Scripts\python.exe -m dbc_compare_tool.cli --old path\to\old --new path\to\new --out report.xlsx
```

## Packaging

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe packaging\dbc_compare_tool.spec
```
