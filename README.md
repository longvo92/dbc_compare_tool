# DBC Compare Tool

[![Test](https://github.com/longvo92/dbc_compare_tool/actions/workflows/test.yml/badge.svg)](https://github.com/longvo92/dbc_compare_tool/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](#requirements)

Desktop utility for comparing Automotive CAN DBC baseline folders and generating an engineering-grade Excel change report.

Point it at an old baseline folder and a new one; it discovers every `.dbc` file, pairs the files (even renamed ones), detects added / removed / modified / renamed messages and signals, and writes a single multi-sheet `.xlsx` report.

![DBC Compare Tool main window](docs/screenshot_main.png)

- [Features](#features)
- [Report layout](#report-layout)
- [Requirements](#requirements)
- [Install](#install)
- [Usage](#usage)
- [Development](#development)
- [Documentation](#documentation)

## Features

- **Folder-level comparison** — recursively discovers all `.dbc` files in both baselines.
- **DBC file pairing** — matches files by relative path first, then by CAN ID overlap and message-layout similarity, so a renamed `.dbc` is still compared as the same file.
- **Manual pairing** — a **Manual Pairing…** dialog lets you choose the new-baseline counterpart for each old file when automatic pairing is not what you want.
- **Message rename detection** — including messages whose CAN ID changed, scored over DLC, transmitter, cycle time, and signal layout.
- **Signal rename detection** — scored over start bit, length, byte order, signedness, factor/offset, unit, and receivers. Name similarity is supporting evidence only.
- **Rename review** — **Run Manual Compare** shows every detected signal rename with its confidence before export; reject one and it is reported as Removed + Added instead.
- **Value tables and comments** — `VAL_` and `CM_` differences are compared for both messages and signals.
- **Change-type filter** — include only Added / Removed / Modified / Renamed in the report.
- **Robust parsing** — an unparsable DBC is flagged `Parse Error` and the rest of the comparison continues; unusual encodings (UTF-8 with/without BOM, CANdb++ default) are handled.
- **CLI mode** — same comparison engine, scriptable for CI or batch runs.

## Report layout

One Excel workbook, five sheets:

| Sheet | Contents |
|---|---|
| `Summary` | Total change counts by category, report title, generation time |
| `DBC Overview` | One row per file pair: status (`Matched` / `DBC Added` / `DBC Removed` / `DBC Renamed` / `Manually Paired` / `Parse Error`), pairing confidence, message/signal counts |
| `Message Details` | Every added, removed, modified, or renamed message |
| `Signal Details` | Every added, removed, modified, or renamed signal |
| `Property Diff` | Before/after row for each changed property |

Rows are color-coded by change type (green = Added, salmon = Removed, yellow = Modified, blue = Renamed). CAN IDs are shown in hexadecimal (`0x1A3`).

## Requirements

- Windows (the UI and path handling target Windows; the core engine is platform-agnostic)
- Python 3.10 or newer
- Runtime dependencies: `cantools`, `openpyxl`, `PySide6` (`pyinstaller` is needed only for `scripts/build.py`)

## Install

Ready-to-run builds are attached to each [release](https://github.com/longvo92/dbc_compare_tool/releases) — download the one-file `.exe` and nothing needs to be installed on the machine.

From source:

```powershell
git clone https://github.com/longvo92/dbc_compare_tool.git
cd dbc_compare_tool
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

The `-e .` step is required: the package lives under `src/`, so `python -m dbc_compare_tool` only resolves after an editable install. It also installs two commands on the `PATH` of the environment: `dbc-compare-tool` (CLI) and `dbc-compare-tool-gui` (desktop app).

## Usage

GUI:

```powershell
.\.venv\Scripts\python.exe -m dbc_compare_tool
```

CLI:

```powershell
.\.venv\Scripts\python.exe -m dbc_compare_tool.cli --old path\to\old --new path\to\new --out report.xlsx
```

All three CLI arguments are required and `--out` must end in `.xlsx`. Exit codes: `0` success, `1` parse or write failure, `2` bad arguments or missing folder.

Quick launchers `run_gui.bat` and `run_cli.bat` at the repository root do the same, using `.venv` in the repo.

Sample baselines for a first run live in [examples/old](examples/old) and [examples/new](examples/new).

## Development

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

CI runs the same suite on Linux and Windows against Python 3.10 and 3.12, plus a CLI comparison of the bundled example baselines. The comparison engine has no UI dependency, so those runs install `cantools` and `openpyxl` only.

Build distributables (zipapp and/or one-file `.exe`):

```powershell
.\.venv\Scripts\python.exe scripts\build.py        # both
.\.venv\Scripts\python.exe scripts\build.py exe    # PyInstaller one-file exe
```

### Project Structure

```
src/dbc_compare_tool/
├── core/
│   ├── discovery.py    # .dbc file discovery in a baseline folder
│   ├── parser.py       # cantools-backed parser: messages, signals, multiplexing,
│   │                   # extended IDs, value tables, comments, selected attributes
│   ├── models.py       # dataclasses for parsed and compared entities
│   ├── comparator.py   # folder- and database-level comparison orchestration
│   └── rename.py       # rename detector interfaces and structural detectors
├── report/excel.py     # Excel report generation
├── ui/main_window.py   # PySide6 desktop application
└── cli.py              # command-line entry point
```

The comparison engine has no UI dependency. See [docs/architecture.md](docs/architecture.md) for the rename-scoring strategy and known limitations.

## Documentation

- [User Guide](resources/help/user_guide.md) — step-by-step usage, also in the app's Help menu
- [Release Notes](resources/help/release_notes.md) — full changelog
- [Architecture](docs/architecture.md) — layers, rename strategy, roadmap

## Contributing

Issues and pull requests are welcome. Please add a test under `tests/` for any change to the comparison or rename-detection logic, and keep the engine free of UI imports so it stays usable from the CLI and CI.

## Author

**Long Vo Thien**

## License

[MIT](LICENSE) © Long Vo Thien
