"""Tests for the release gate.

scripts/release_check.py is what stands between a typo and a tag that cannot be
taken back, so its parsing is tested like engine code. The last test runs it
against the real project files, which is what keeps the gate honest as those
files change.
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "release_check.py"

_spec = importlib.util.spec_from_file_location("release_check", _SCRIPT)
release_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release_check)


_NOTES = """# DBC Compare Tool - Release Notes

## Version 0.2.0

### Added

- Signal Focus tab.

---
## Version 0.1.8

### Added

- Manual DBC pairing.
"""


class VersionSourceTests(unittest.TestCase):
    def test_reads_the_version_from_init(self):
        text = '"""Doc."""\n\n__version__ = "1.2.3"\n'
        self.assertEqual(release_check.read_init_version(text), "1.2.3")

    def test_missing_init_version_is_an_error(self):
        with self.assertRaises(release_check.ReleaseCheckError):
            release_check.read_init_version("__ver__ = 'nope'")

    def test_reads_the_version_from_pyproject(self):
        text = '[project]\nname = "dbc-compare-tool"\nversion = "1.2.3"\n'
        self.assertEqual(release_check.read_pyproject_version(text), "1.2.3")

    def test_rejects_a_version_that_is_not_x_y_z(self):
        for bad in ("0.2", "v0.2.0", "0.2.0-rc1", "latest"):
            with self.subTest(version=bad):
                self.assertIsNone(release_check.VERSION_PATTERN.match(bad))


class ReleaseNotesTests(unittest.TestCase):
    def test_extracts_only_the_newest_section(self):
        notes = release_check.extract_release_notes(_NOTES, "0.2.0")
        self.assertIn("Signal Focus tab", notes)
        self.assertNotIn("Manual DBC pairing", notes)
        self.assertFalse(notes.endswith("-"), "the --- separator must not leak into the notes")

    def test_an_older_section_is_refused(self):
        # Releasing 0.1.8 while 0.2.0 sits on top means the bump PR was not merged.
        with self.assertRaises(release_check.ReleaseCheckError):
            release_check.extract_release_notes(_NOTES, "0.1.8")

    def test_an_empty_section_is_refused(self):
        with self.assertRaises(release_check.ReleaseCheckError):
            release_check.extract_release_notes("# Notes\n\n## Version 0.3.0\n\n", "0.3.0")

    def test_a_file_without_sections_is_refused(self):
        with self.assertRaises(release_check.ReleaseCheckError):
            release_check.extract_release_notes("# Notes\n\nnothing here\n", "0.3.0")

    def test_the_last_section_runs_to_the_end_of_the_file(self):
        single = "# Notes\n\n## Version 0.3.0\n\n### Added\n\n- One thing.\n"
        self.assertIn("One thing", release_check.extract_release_notes(single, "0.3.0"))


class RealRepositoryTests(unittest.TestCase):
    """The gate has to pass on the version this repository currently declares."""

    def setUp(self):
        init_text = (_REPO_ROOT / "src" / "dbc_compare_tool" / "__init__.py").read_text(encoding="utf-8")
        self.version = release_check.read_init_version(init_text)

    def test_the_declared_version_is_release_ready(self):
        notes = release_check.check(self.version)
        self.assertTrue(notes.strip())

    def test_pyproject_agrees_with_the_package(self):
        pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(release_check.read_pyproject_version(pyproject), self.version)

    def test_a_version_the_repository_does_not_declare_is_refused(self):
        with self.assertRaises(release_check.ReleaseCheckError):
            release_check.check("99.99.99")

    def test_notes_are_written_when_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "RELEASE_NOTES.md"
            target.write_text(release_check.check(self.version) + "\n", encoding="utf-8")
            self.assertTrue(target.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
