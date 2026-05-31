# Architecture

## Goals

This project is a local Windows desktop application for automotive engineers comparing DBC releases. The core comparison logic is kept independent from the UI so it can be tested, reused from CLI, and packaged safely.

## Layers

1. Parser
   - Reads `.dbc` files.
   - Extracts messages, signals, and common message cycle-time attributes.
   - Keeps parsed output in small dataclasses.

2. Comparison Engine
   - Discovers `.dbc` files in old and new baseline folders.
   - Compares files with the same relative path first.
   - Pairs old-only and new-only `.dbc` files by CAN ID overlap and message-layout similarity.
   - Treats still-unmatched files as added or removed message groups.
   - Delegates rename decisions to detector components.

3. Rename Detection Engine
   - Pluggable detector interface.
   - Current implementation uses deterministic structural scoring.
   - Name similarity has low weight and cannot dominate structural mismatch.

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

Message rename scoring prioritizes:

- CAN ID
- DLC
- Transmitter
- Cycle time
- Signal count
- Signal layout
- Name similarity as supporting evidence only

Signal rename scoring prioritizes:

- Start bit
- Length
- Byte order
- Signedness
- Factor
- Offset
- Unit
- Receivers
- Name similarity as supporting evidence only

The detector uses greedy one-to-one matching over candidates above threshold. This is simple, debuggable, and appropriate for baseline comparison sizes typically seen in CAN projects.

## Known Risks

- DBC files can contain advanced constructs not yet parsed, such as multiplexing semantics, extended attributes, value tables, and comments.
- CAN FD and extended-frame handling may need project-specific interpretation.
- Rename thresholds may need calibration against real release history.
- PySide6 packaging should be validated on the same Windows/Python version used for release builds.

## Incremental Roadmap

1. Core parser, comparison, rename detection, and Excel report.
2. Desktop UI workflow.
3. Real-project calibration tests using anonymized DBC baselines.
4. Packaging smoke test on a clean Windows machine.
5. Optional richer parsing if engineers need comments, value tables, multiplexing, or attributes in reports.
