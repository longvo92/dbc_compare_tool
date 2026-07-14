from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dbc_compare_tool.core.comparator import DbcComparator
from dbc_compare_tool.core.parser import DbcParseError
from dbc_compare_tool.report.excel import write_excel_report


def main() -> int:
    # Windows consoles often use cp1252; replace unencodable characters
    # instead of crashing when file paths or DBC content contain them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="Compare DBC baseline folders and generate an Excel report.")
    parser.add_argument("--old", required=True, type=Path, help="Old baseline folder")
    parser.add_argument("--new", required=True, type=Path, help="New baseline folder")
    parser.add_argument("--out", required=True, type=Path, help="Output .xlsx report path")
    args = parser.parse_args()

    if args.out.suffix.lower() != ".xlsx":
        print(f"Error: output path must end with .xlsx: {args.out}", file=sys.stderr)
        return 2

    try:
        result = DbcComparator().compare_folders(args.old, args.new, progress_callback=print)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except DbcParseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        write_excel_report(result, args.out)
    except OSError as exc:
        print(f"Error: unable to write report {args.out}: {exc}", file=sys.stderr)
        return 1

    parse_errors = [fp for fp in result.file_pairs if fp.status == "Parse Error"]
    for fp in parse_errors:
        print(f"Warning: skipped unparsable DBC: {fp.dbc_file}", file=sys.stderr)

    print(f"Report written: {args.out}")
    print(f"Total changes: {result.summary()['Total Changes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
