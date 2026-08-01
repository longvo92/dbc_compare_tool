# User Guide

The tool has two tabs. **Baseline Compare** reports every change between two DBC baselines.
**Signal Focus** reports what changed for the software on one ECU — see
[Signal Focus](#signal-focus) below.

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

## Signal Focus

Use this tab when you work on the application layer of one ECU and care about the signals themselves
— data type, scaling, range, unit, value table, init value — not about which message carries them or
how often it is sent.

### Steps

1. Select the **Old** and **New Baseline Folder**. Switching to this tab copies the folders from the
   Baseline Compare tab if you have not filled them in yet.
2. Click **Load & Pair DBC**. Files are paired the same way as in the baseline comparison, including
   renamed files, and the ECU nodes of each file are loaded.
3. For every pair, pick the ECU node your software runs on — separately for the old and the new side,
   so a node renamed between baselines still works. **Apply First Node To All** copies your first
   choice to every other pair offering the same node name. Leave both drop-downs on `— none —` to
   skip a pair.
4. Paste your application's signal list into the text box, or click **Import .txt…**. One name per
   line; comment lines starting with `#` or `//` are skipped, and everything after the first comma,
   semicolon, or tab is ignored, so you can paste straight out of Excel. Leave the box empty to audit
   every signal of the node.
5. Click **Run Signal Compare**. The result appears in the table below; tick **Show only signals
   needing review** to hide everything that is fine.
6. Click **Export Excel** to write the report.

### Signal Statuses

* **Removed** — the signal is gone from the DBC. Your code breaks. If a new signal has exactly the
  same properties, its name is given in the note as a possible rename.
* **Modified** — data type, scaling, range, unit, value table, or init value changed. Check every
  place the signal is read or written.
* **Added** — a new signal for this node.
* **Direction Changed** — the ECU now sends what it used to receive, or the reverse. The port
  direction in your software has to follow.
* **Out Of Node Scope** — the signal is still in the DBC but is no longer sent to or from your node.
  Usually a routing or receiver-list change rather than a deleted signal.
* **Ambiguous** — the same name is defined more than once with different properties. Decide which one
  you mean; the tool refuses to guess.
* **Not In DBC** — the name is in your signal list but in none of the compared files. Almost always a
  typo in the list.
* **Moved** — only the carrying message, CAN ID, or bit position changed. Nothing to do; your
  interface is unaffected.
* **Unchanged** — no application-relevant difference.

Start bit, byte order, CAN ID, DLC, cycle time, and transmitter are never reported as changes here.
They belong to the communication stack, not to your application. Use the **Baseline Compare** tab
when you do need them.

### The Report

* **Signal Focus Summary** — the node selected per DBC pair, the size of your signal list, and how
  many signals fall into each status. **Needs Review** counts everything except `Moved` and
  `Unchanged`.
* **Signal Focus** — one row per signal, with its current properties and both carrier frames.
* **Property Diff (App)** — one row per changed property, old value in salmon, new value in green.
* **Value Table Diff** — one row per changed `VAL_` entry, marked **Relabeled**, **Value Added**, or
  **Value Removed**. Read the relabeled ones first: the raw value kept its number but changed its
  meaning, so your code still builds and now behaves wrongly.

---

## Tips

* Drag a folder from Windows Explorer directly onto the baseline fields — no need to click Browse.
* Drag the divider between the input panel and the Execution Log to resize the log area.
* Untick change types you don't need before running to get a smaller, focused report.
* If the report fails to save, make sure the file is not currently open in Excel.
* In **Signal Focus**, keep your application's signal list in a `.txt` file next to the project and
  re-import it for every baseline — the report then reads in the same order as your list.
* If a node shows almost no received signals, check the DBC: receivers left as `Vector__XXX` are not
  attributed to any node.
