# Architecture

## Goals

This project is a local Windows desktop application for automotive engineers comparing DBC releases. The core comparison logic is kept independent from the UI so it can be tested, reused from CLI, and packaged safely.

## Layers

1. Parser
   - Reads `.dbc` files through cantools.
   - Extracts messages, signals, multiplexing metadata, extended-frame state, and common message cycle-time attributes.
   - Keeps parsed output in small dataclasses.

2. Comparison Engine
   - Discovers `.dbc` files in old and new baseline folders.
   - Compares files with the same relative path first.
   - Pairs old-only and new-only `.dbc` files by CAN ID overlap and message-layout similarity.
   - Treats still-unmatched files as added or removed message groups.
   - Applies exact frame ID and bit-layout rename rules for messages and signals.

3. Rename Detection Engine
   - Message renames require the same normalized frame ID and a different message name.
   - Signal renames require the same frame ID, start bit, length, byte order, and a different signal name.
   - DBC file pairing still uses deterministic structural scoring so renamed `.dbc` files can be compared.

4. Report Generator
   - Writes a single Excel workbook.
   - Always writes exactly three sheets: `Summary`, `Message Details`, and `Signal Details`.

5. UI Layer
   - PySide6 desktop UI.
   - Runs comparison on a worker thread to keep the UI responsive.

6. Packaging Layer
   - PyInstaller spec for producing a standalone Windows application.

## Rename Strategy

DBC file pairing prioritizes:

- CAN ID overlap
- Common message structural similarity
- Message-name overlap
- File-name similarity as supporting evidence only

Message rename detection uses normalized frame ID equality. Signal rename detection uses greedy one-to-one matching over exact bit-layout candidates within the same frame ID.

## Known Risks

- Project-specific attributes beyond cycle time may need to be added to reports if engineers want them surfaced.
- CAN FD handling may need project-specific interpretation.
- DBC file rename pairing thresholds may need calibration against real release history.
- PySide6 packaging should be validated on the same Windows/Python version used for release builds.

## Incremental Roadmap

1. Core parser, comparison, rename detection, and Excel report.
2. Desktop UI workflow.
3. Real-project calibration tests using anonymized DBC baselines.
4. Packaging smoke test on a clean Windows machine.
5. Optional richer reporting if engineers need comments, value tables, or additional attributes in reports.
