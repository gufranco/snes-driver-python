import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import snesdriver


def copies_a_version(source: str) -> bool:
    return re.search(r"""^VERSION\s*[:=][^=\n]*=?\s*["']""", source, re.M) is not None


def stamped() -> str:
    line = next(
        one
        for one in (ROOT / "snesdriver" / "version.py").read_text().splitlines()
        if one.startswith("VERSION = ")
    )
    return line.split('"')[1]


class VersionTest(unittest.TestCase):
    def test_it_reads_as_three_numbers(self) -> None:
        # Arrange
        pattern = r"^\d+\.\d+\.\d+([-+].*)?$"

        # Act
        held = snesdriver.VERSION

        # Assert
        self.assertRegex(held, pattern)

    def test_the_package_reports_the_version_the_release_stamped(self) -> None:
        # Arrange
        held = stamped()

        # Act
        reported = (snesdriver.VERSION, snesdriver.__version__)

        # Assert
        self.assertEqual(reported, (held, held))

    def test_the_release_script_writes_the_field_this_file_holds(self) -> None:
        # Arrange
        wanted = "snesdriver/version.py"

        # Act
        script = (ROOT / "scripts" / "set-version.sh").read_text()

        # Assert
        self.assertIn(wanted, script)

    def test_nothing_else_in_the_package_carries_a_version(self) -> None:
        # Arrange
        package = ROOT / "snesdriver"

        # Act
        elsewhere = [
            path.name
            for path in package.glob("*.py")
            if path.name != "version.py" and copies_a_version(path.read_text())
        ]

        # Assert
        self.assertEqual(elsewhere, [])

    def test_and_a_hardcoded_copy_would_be_caught(self) -> None:
        # Arrange
        source = 'VERSION = "1.2.3"'

        # Act
        found = copies_a_version(source)

        # Assert
        self.assertTrue(found)

    def test_while_a_version_read_out_of_the_one_file_is_not(self) -> None:
        # Arrange
        source = "VERSION = installed_version()"

        # Act
        found = copies_a_version(source)

        # Assert
        self.assertFalse(found)


if __name__ == "__main__":
    unittest.main()
