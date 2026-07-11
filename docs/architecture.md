# Architecture

## Goals

This project is a local Windows desktop application for automotive engineers comparing DBC releases. The core comparison logic is kept independent from the UI so it can be tested, reused from CLI, and packaged safely.

## Layers

1. Parser
   - Reads `.dbc` files through cantools.
   - Extracts messages, signals, multiplexing metadata, extended-frame state, value tables (`VAL_`), comments (`CM_`), and common message cycle-time attributes.
   - Keeps parsed output in small dataclasses.

2. Comparison Engine
   - Discovers `.dbc` files in old and new baseline folders.
   - Compares files with the same relative path first.
   - Pairs old-only and new-only `.dbc` files by CAN ID overlap and message-layout similarity.
   - Matches messages by frame ID first; still-unmatched messages run through structural rename detection before being treated as added/removed.
   - Compares value tables and comments as regular properties, surfaced in change descriptions and the Property Diff sheet.

3. Rename Detection Engine
   - Messages with the same normalized frame ID and a different name are exact renames (confidence 1.0).
   - Messages whose frame ID also changed are matched via `MessageRenameDetector`, a structural scorer over DLC, transmitter, cycle time, signal count, and signal-layout overlap (name similarity is minor supporting evidence).
   - Signal renames require the same frame ID; unmatched signals are scored the same way via `SignalRenameDetector`, with a relaxed name-driven mode for Event Matrix-style messages.
   - DBC file pairing still uses deterministic structural scoring so renamed `.dbc` files can be compared.

4. Report Generator
   - Writes a single Excel workbook.
   - Writes five sheets in order: `Summary`, `DBC Overview`, `Message Details`, `Signal Details`, and `Property Diff`.

5. UI Layer
   - PySide6 desktop UI.
   - Runs comparison on a worker thread to keep the UI responsive.
   - Persists last-used folder paths via `QSettings("VinFast", "DBCCompareTool")` (Windows registry).

6. Packaging Layer
   - PyInstaller spec for producing a standalone Windows application.

## Rename Strategy

DBC file pairing prioritizes:

- CAN ID overlap
- Common message structural similarity
- Message-name overlap
- File-name similarity as supporting evidence only

Message rename detection prefers normalized frame ID equality; when frame ID also changes, unmatched messages fall back to `MessageRenameDetector` structural scoring (threshold 0.60). Signal rename detection uses greedy one-to-one matching over exact bit-layout candidates within the same frame ID, then falls back to `SignalRenameDetector` scoring for the rest.

## Known Risks

- Project-specific attributes beyond cycle time may need to be added to reports if engineers want them surfaced.
- CAN FD handling may need project-specific interpretation.
- DBC file rename pairing thresholds may need calibration against real release history.
- `MessageRenameDetector` threshold (0.60) trades off false positives vs. missed CAN-ID-changed renames; may need recalibration against real release history.
- PySide6 packaging should be validated on the same Windows/Python version used for release builds.

## Incremental Roadmap

1. Core parser, comparison, rename detection, and Excel report. *(done)*
2. Desktop UI workflow. *(done)*
3. Message rename detection for CAN-ID changes, and value table/comment comparison. *(done)*
4. Real-project calibration tests using anonymized DBC baselines.
5. Packaging smoke test on a clean Windows machine.
