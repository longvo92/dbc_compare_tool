# Architecture

## Goals

This project is a local Windows desktop application for automotive engineers comparing DBC releases. The core comparison logic is kept independent from the UI so it can be tested and reused from CLI.

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
   - PySide6 desktop UI with an application-wide stylesheet.
   - Runs comparison on a worker thread to keep the UI responsive.
   - Persists last-used folder paths via `QSettings("DbcCompareTool", "DBCCompareTool")` (Windows registry).

## Rename Strategy

DBC file pairing prioritizes:

- CAN ID overlap
- Common message structural similarity
- Message-name overlap
- File-name similarity as supporting evidence only

Message rename detection prefers normalized frame ID equality; when frame ID also changes, unmatched messages fall back to `MessageRenameDetector` structural scoring (threshold 0.60). Signal rename detection uses greedy one-to-one matching over exact bit-layout candidates within the same frame ID, then falls back to `SignalRenameDetector` scoring for the rest.

## Validation Status

The tool has been exercised against real project DBC baselines of several kinds, not only the
bundled examples. The rename thresholds held up on that material and were **not** changed as a
result: `MessageRenameDetector` stays at 0.60 and DBC file pairing at `FILE_RENAME_THRESHOLD = 0.55`.
Treat those numbers as field-confirmed defaults rather than initial guesses.

What that field testing did **not** cover yet — these remain unvalidated outside the unit suite:

| Area | Status |
|---|---|
| CAN FD databases | Not exercised on real baselines |
| Extended / mixed frame IDs | Unit-tested only (`TestExtendedStandardFrameCollision` covers a standard frame hidden by an extended twin) |
| Multiplexed signals | Parsed and carried through comparison, but not exercised on real multiplexed baselines |
| Vendor attributes (`BA_`) beyond cycle time, very large databases | Not exercised |

## Known Risks

- `BA_` attributes other than cycle time are not read at all (`parser.py` takes `cycle_time` from
  cantools and nothing else), so a project that encodes meaning in custom attributes will see no
  diff for them. Surfacing one means extending the parser, the models, and the Property Diff sheet.
- CAN FD handling may still need project-specific interpretation — see the table above.
- The rename thresholds are a deliberate trade-off: at 0.60, `MessageRenameDetector` favours missing
  a CAN-ID-changed rename (reported as Removed + Added) over inventing a wrong one. Field use has not
  shown a reason to move it, but a project with heavy simultaneous ID-and-name churn may want it lower.
- Rename review in the UI is the intended safety net for the above: a detected rename can always be
  rejected before export, but a *missed* rename has no equivalent "merge these two" affordance.

## Incremental Roadmap

1. Core parser, comparison, rename detection, and Excel report. *(done)*
2. Desktop UI workflow. *(done)*
3. Message rename detection for CAN-ID changes, and value table/comment comparison. *(done)*
4. Real-project validation of the rename thresholds. *(done — thresholds unchanged)*
5. Coverage for the gaps listed under Validation Status, starting with CAN FD and multiplexed
   baselines.
