# Main Features

## Automatic DBC File Matching

The tool automatically matches DBC files between Baseline and Current folders.

Matching is not based solely on file names. If a DBC file is renamed while its content remains substantially unchanged, the tool can still identify it as the same DBC and compare the corresponding files.

Example:

Baseline:

* BCM.dbc

Current:

* BCM_V2.dbc

Result:

* Detected as a renamed DBC file rather than one removed and one added file.

---

## Message Rename Detection

The tool can identify message renames even when the message name changes.

Detection is based on:

* CAN ID
* DLC
* Signal layout
* Signal composition
* Message attributes

Example:

Baseline:

* VehicleStatus

Current:

* Vehicle_Status

Result:

* Classified as Message Rename.

---

## Signal Rename Detection

The tool can identify signal renames by comparing technical characteristics rather than relying solely on signal names.

Detection considers:

* Start Bit
* Length
* Byte Order
* Signedness
* Scaling (Factor / Offset)
* Unit
* Receivers
* Signal layout within the message

Example:

Baseline:

* VehSpd

Current:

* VehicleSpeed

Result:

* Classified as Signal Rename.

---

## Possible Rename Detection

For messages containing many structurally similar signals (such as Event Matrix messages), rename detection may be ambiguous.

In such cases, the tool reports:

* Possible Rename

instead of:

* Rename

This reduces false-positive rename classifications and improves report reliability.

---

## Excel Report Generation

The tool generates a structured Excel report containing:

* Summary
* DBC Overview
* Message Changes
* Signal Changes
* Rename Information
* Possible Rename Information
* Detailed Modification Tracking