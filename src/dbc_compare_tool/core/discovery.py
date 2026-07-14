from __future__ import annotations

from pathlib import Path

from dbc_compare_tool.core.models import FilePair


def discover_dbc_pairs(old_folder: Path, new_folder: Path) -> list[FilePair]:
    old_files = _collect(old_folder)
    new_files = _collect(new_folder)
    relative_paths = sorted(set(old_files) | set(new_files))
    return [
        FilePair(relative_path=relative, old_path=old_files.get(relative), new_path=new_files.get(relative))
        for relative in relative_paths
    ]


def _collect(folder: Path) -> dict[str, Path]:
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folder does not exist: {folder}")
    # Match the extension case-insensitively so *.DBC is found on
    # case-sensitive filesystems too (rglob("*.dbc") would miss it there).
    return {
        path.relative_to(folder).as_posix(): path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() == ".dbc"
    }

