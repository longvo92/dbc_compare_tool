# User Guide

## Getting Started

1. **Old Baseline Folder** — select (or drag & drop) the folder containing the previous DBC baseline.
2. **New Baseline Folder** — select (or drag & drop) the folder containing the new DBC baseline.
3. **Report Path** — choose where to save the Excel report (`.xlsx`).
4. **Include Change Types** — tick the change categories you want in the report (Added / Removed / Modified / Renamed). All are included by default.
5. Click **Run Auto Compare** for automatic file matching, or **Run Manual Compare** to use file pairs you chose yourself in the **Manual Pairing** dialog (see below). Progress appears in the Execution Log. When finished, click **Open Report** to view the result in Excel.

The tool remembers your last-used folders and report path, so the next session starts pre-filled.

---

## Understanding the Report

The Excel report contains the following sheets:

* **Summary** — total change counts by category, with report title and generation time.
* **DBC Overview** — one row per DBC file pair: pairing status (`Matched` / `DBC Added` / `DBC Removed` / `DBC Renamed` / `Manually Paired` / `Parse Error`), pairing confidence, and message/signal counts for both baselines.
* **Message Details** — every added, removed, modified, or renamed message.
* **Signal Details** — every added, removed, modified, or renamed signal.
* **Property Diff** — before/after table for every changed property, one row per property. Old values highlighted in salmon, new values in green.

Rows are color-coded by change type: green = Added, salmon = Removed, yellow = Modified, blue = Renamed. CAN IDs are shown in hexadecimal (e.g. `0x1A3`).

---

## Main Features

### Automatic DBC File Matching

DBC files are matched between the two folders automatically. Matching is not based solely on file names: if a DBC file was renamed while its content remains substantially unchanged, the tool still identifies it as the same DBC and compares the pair.

Example: `BCM.dbc` (old) vs `BCM_V2.dbc` (new) — detected as a renamed DBC file, not as one removed and one added file.

### Manual DBC Pairing

If automatic matching does not pair the files the way you want, choose the pairs yourself:

1. Select both baseline folders, then click **Manual Pairing…** to open the pairing dialog.
2. For each old-baseline file, pick its new-baseline counterpart from the drop-down — or `— Removed (no pair) —` to report it as removed. New-baseline files not selected in any pair are reported as added.
3. Click **Save** to store the pairing, then click **Run Manual Compare**.

Clicking **Run Manual Compare** without a saved pairing simply uses automatic file matching — you still get the signal-rename review step. Manually matched pairs with different file names appear as **Manually Paired** on the DBC Overview sheet. Each new file can only be used in one pair. Changing either baseline folder discards the saved pairing — open the dialog again. **Run Auto Compare** always uses automatic matching, regardless of any saved pairing.

### Message Rename Detection

Message renames are identified even when the message name changes, based on CAN ID, DLC, signal layout, signal composition, and message attributes.

Example: `VehicleStatus` renamed to `Vehicle_Status` — classified as **Renamed**, with a `Matched by: ...` explanation in the report.

### Signal Rename Detection

Signal renames are identified by comparing technical characteristics — start bit, length, byte order, signedness, scaling (factor/offset), unit, receivers, and layout within the message — rather than relying on names alone.

Example: `VehSpd` renamed to `VehicleSpeed` — classified as **Renamed**.

### Reviewing Renamed Signals

Rename detection is heuristic, so **Run Manual Compare** lets you double-check it before the report is written: after the comparison finishes, a dialog lists every auto-detected signal rename with its confidence score and level (hover a row to see the match reasons and property changes).

* Leave a row checked to **accept** the rename — it is reported as **Renamed**, as usual.
* Uncheck a row to **reject** it — the report shows the old signal as **Removed** and the new signal as **Added** instead.
* **Accept All** / **Reject All** buttons handle long lists; **Cancel** keeps all detected renames.

**Run Auto Compare** skips this step and keeps every detected rename automatically.

### Confidence Levels

Every detected rename carries a confidence score and a level — **High**, **Medium**, or **Low** — shown in the report and in the rename review dialog. Use it to decide how much of the result needs a second look; anything below High is worth checking.

Two situations lower confidence on purpose:

* **Event Matrix messages** — messages containing many structurally similar signals. There, the technical properties carry almost no information (dozens of signals share them), so the signal name drives the match and confidence never reaches High. Review these rows.
* **Ambiguous matches** — when several old signals are equally plausible matches for one new signal, all of them are downgraded and the report notes `Ambiguous: ...` in the match reasons.

### Robust File Handling

* A corrupt or unparsable DBC file does not stop the comparison: it is marked **Parse Error** (highlighted red in DBC Overview) and the remaining files are still compared.
* Files with special characters or unusual encodings (UTF-8 with/without BOM, CANdb++ default encoding) open reliably.

---

## Tips

* Drag a folder from Windows Explorer directly onto the baseline fields — no need to click Browse.
* Drag the divider between the input panel and the Execution Log to resize the log area.
* Untick change types you don't need before running to get a smaller, focused report.
* If the report fails to save, make sure the file is not currently open in Excel.
