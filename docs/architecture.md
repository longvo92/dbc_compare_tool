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

## Scoring Reference

Every score below is a weighted sum of independent checks, capped at 1.0. A pair is only considered
a rename when its score reaches the detector's threshold. All weights are literal constants in the
source — this section is the authoritative description of them, so update both together.

Each weight set sums to exactly 1.0, so a perfect match on every criterion scores 1.0 and the weights
read directly as "share of the decision". The one exception is the event-like signal set, which tops
out at 0.88; that is explained below.

### DBC file pairing — `_score_database_pair` (comparator.py)

Applied only to files left over after relative-path matching. Threshold: `FILE_RENAME_THRESHOLD = 0.55`.
A pair sharing no frame key at all scores 0.0 and is never paired.

| Criterion | Weight | Measure |
|---|---|---|
| CAN ID overlap | 0.55 | `common frame keys / max(old count, new count)`, keyed by `(can_id, is_extended_frame)` |
| Common-ID structure | 0.25 | Mean structure score over the shared frame keys (table below) |
| Message-name overlap | 0.15 | `common message names / max(old count, new count)` |
| File-name similarity | 0.05 | `SequenceMatcher` ratio over the lowercased relative paths |

Structure score per shared frame key — `_common_message_structure_score`:

| Criterion | Weight |
|---|---|
| DLC equal | 0.20 |
| Transmitter equal | 0.15 |
| Cycle time equal | 0.10 |
| Signal count equal | 0.15 |
| Signal-layout Jaccard | 0.40 × overlap |

Signal layout is the set of `(start_bit, length, byte_order)` tuples of a message's signals, compared
with a Jaccard index (`|A ∩ B| / |A ∪ B|`; two empty sets score 1.0, one empty set scores 0.0).

### Message rename — `MessageRenameDetector` (rename.py)

Reached only when the frame ID changed too: a message with the same frame key and a different name is
already an exact rename with confidence 1.0 and never goes through scoring. Threshold: **0.60**.

| Criterion | Weight |
|---|---|
| CAN ID equal | 0.35 |
| Signal-layout Jaccard | 0.22 × overlap |
| DLC equal | 0.12 |
| Signal count equal | 0.10 |
| Transmitter equal | 0.08 |
| Cycle time equal | 0.08 (skipped when the old cycle time is unknown) |
| Name similarity | 0.05 × ratio |

### Signal rename — `SignalRenameDetector` (rename.py)

Applied per message, to signals left unmatched after exact name and bit-layout matching. Two weight
sets; the parent message decides which one is used.

| Criterion | Normal (threshold **0.82**) | Event-like (threshold **0.65**) |
|---|---|---|
| Start bit equal | 0.18 | 0.06 |
| Length equal | 0.18 | 0.06 |
| Byte order equal | 0.10 | 0.05 |
| Signedness equal | 0.06 | 0.03 |
| Factor equal | 0.12 | 0.04 |
| Offset equal | 0.12 | 0.04 |
| Unit equal | 0.08 | 0.04 |
| Receivers equal | 0.11 | 0.06 |
| Name similarity | 0.05 × ratio | **0.50 × ratio** |

The event-like column deliberately inverts the priority: in an Event Matrix message dozens of signals
share identical technical properties, so structure is nearly worthless as evidence and the name
carries the decision. Note the consequence — structural checks there total 0.38, so an event-like
match maxes out at 0.88 and can never be reported as High confidence.

A message counts as event-like (`EventMessageDetector.is_event_like`) when **all** of: it has at least
5 signals, at least 70% of them are ≤ 4 bits, and at least 60% share the same
`(length, byte_order, factor, offset, unit)` signature.

### Matching procedure and confidence

All old×new pairs are scored, those at or above the threshold become candidates, then candidates are
taken in descending score order with each old and each new item used at most once (greedy one-to-one).

Before that, ambiguity is penalised: when *n* old items are candidates for the same new item, each of
those candidates loses `0.15 × (n − 1)`, floored at 0.70, and gains an "Ambiguous" reason. Two details
follow from the order of operations — the penalty is applied *after* the threshold filter, so a
penalised pair can end up scoring below its own detector threshold and still be matched, and the 0.70
floor means an ambiguous match is never downgraded below Medium.

Confidence levels shown in the UI and report: **High** ≥ 0.90, **Medium** ≥ 0.70, otherwise **Low**.

## Validation Status

The tool has been exercised against real project DBC baselines of several kinds, not only the
bundled examples. The rename thresholds held up on that material and were **not** changed as a
result: DBC file pairing at `FILE_RENAME_THRESHOLD = 0.55`, `MessageRenameDetector` at 0.60, and
`SignalRenameDetector` at 0.82 (0.65 for event-like messages). Treat those numbers as field-confirmed
defaults rather than initial guesses; the weights behind them are documented under
[Scoring Reference](#scoring-reference).

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
