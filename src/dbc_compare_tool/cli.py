from __future__ import annotations

import argparse
from pathlib import Path

from dbc_compare_tool.core.comparator import DbcComparator
from dbc_compare_tool.report.excel import write_excel_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare DBC baseline folders and generate an Excel report.")
    parser.add_argument("--old", required=True, type=Path, help="Old baseline folder")
    parser.add_argument("--new", required=True, type=Path, help="New baseline folder")
    parser.add_argument("--out", required=True, type=Path, help="Output .xlsx report path")
    args = parser.parse_args()

    result = DbcComparator().compare_folders(args.old, args.new)
    write_excel_report(result, args.out)
    print(f"Report written: {args.out}")
    print(f"Total changes: {result.summary()['Total Changes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

