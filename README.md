# DBC Compare Tool

Desktop utility for comparing Automotive CAN DBC baseline folders and generating an engineering-grade Excel report.

## What It Does

- Select an old baseline folder and a new baseline folder.
- Automatically discovers all `.dbc` files.
- Detects added, removed, modified, and renamed messages.
- Detects added, removed, modified, and renamed signals.
- Generates one Excel workbook with exactly three sheets:
  - `Summary`
  - `Message Details`
  - `Signal Details`

Rename detection uses structural matching first. Name similarity is only supporting evidence.

## Architecture

- `parser`: Lightweight DBC parser for messages, signals, and selected attributes.
- `comparison`: Folder and database comparison orchestration.
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

