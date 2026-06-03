# DBC Compare Tool - User Guide

## Purpose

DBC Compare Tool compares two DBC baseline folders and generates an Excel report that shows message and signal changes.

## Quick Start

1. Open the application.
2. Select the old baseline folder.
3. Select the new baseline folder.
4. Choose the Excel report output path.
5. Click Run Comparison.
6. Click Open Report when the comparison is complete.

## Excel Report

The generated workbook contains:

- Summary: total counts for added, removed, modified, and renamed items.
- Message Details: message-level changes.
- Signal Details: signal-level changes.

## Change Description

Changed values are shown as old -> new.

Examples:

- Signal Name: VehicleSpeed -> VehSpd
- Layout changed: Start Bit: 0 -> 8, Length: 16 -> 8
- Min: 0 -> 7
- Max: 250 -> 260