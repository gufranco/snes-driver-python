import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from snesdriver import version


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
            if path.name != "version.py" and re.search(r"^VERSION = ", path.read_text(), re.M)
        ]

        self.assertEqual(elsewhere, [])


if __name__ == "__main__":
    unittest.main()
