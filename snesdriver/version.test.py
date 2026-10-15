import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from snesdriver import version


def _copies_a_version(source: str) -> bool:
    return re.search(r"""^VERSION\s*[:=][^=\n]*=?\s*["']""", source, re.M) is not None


class VersionTest(unittest.TestCase):
    def test_a_version_is_recorded(self) -> None:
        self.assertTrue(version.VERSION)

    def test_it_reads_as_three_numbers(self) -> None:
        self.assertRegex(version.VERSION, r"^\d+\.\d+\.\d+([-+].*)?$")

    def test_the_release_script_writes_the_field_this_file_holds(self) -> None:
        script = (ROOT / "scripts" / "set-version.sh").read_text()

        self.assertIn("snesdriver/version.py", script)

    def test_nothing_else_in_the_package_carries_a_version(self) -> None:
        elsewhere = [
            path.name
            for path in (ROOT / "snesdriver").glob("*.py")
            if path.name != "version.py" and _copies_a_version(path.read_text())
        ]

        self.assertEqual(elsewhere, [])

    def test_and_a_hardcoded_copy_would_be_caught(self) -> None:
        self.assertTrue(_copies_a_version('VERSION = "1.2.3"'))

    def test_while_a_version_read_out_of_the_one_file_is_not(self) -> None:
        self.assertFalse(_copies_a_version("VERSION = _version()"))


if __name__ == "__main__":
    unittest.main()
