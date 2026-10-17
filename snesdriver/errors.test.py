from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import snesdriver

SOURCE = ROOT / "snesdriver" / "errors.py"


def reaching_back(source: str) -> list[str]:

    def inside(name: str) -> bool:
        return name.startswith(".") or name == "snesdriver" or name.startswith("snesdriver.")

    borrowed = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            borrowed += [alias.name for alias in node.names if inside(alias.name)]
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            if inside(name):
                borrowed.append(name)
    return borrowed


def defined_errors() -> list[str]:
    tree = ast.parse(SOURCE.read_text())
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


class OneHomeTest(unittest.TestCase):
    def test_the_module_defines_the_refusal_this_package_makes(self) -> None:
        # Arrange
        source = SOURCE

        # Act
        found = defined_errors()

        # Assert
        self.assertEqual(found, ["UnknownPart"], source.name)

    def test_the_package_exports_each_one_under_its_own_name(self) -> None:
        # Arrange
        names = defined_errors()

        # Act
        found = {
            name: getattr(snesdriver, name).__module__
            for name in names
            if name in snesdriver.__all__
        }

        # Assert
        self.assertEqual(found, dict.fromkeys(names, "snesdriver.errors"))

    def test_and_each_derives_from_exception(self) -> None:
        # Arrange
        names = defined_errors()

        # Act
        kinds = [issubclass(getattr(snesdriver, name), Exception) for name in names]

        # Assert
        self.assertEqual(kinds, [True] * len(names))

    def test_naming_a_part_this_package_does_not_cover_raises_the_one_defined_here(self) -> None:
        # Arrange
        part = "cx4"

        # Act
        with self.assertRaises(snesdriver.UnknownPart) as caught:
            snesdriver.window_for(part, "lorom")

        # Assert
        self.assertEqual(
            str(caught.exception),
            "cx4 is not a part with a known window; there are dsp, obc1, st, st018",
        )


class NoCycleTest(unittest.TestCase):
    def test_it_imports_nothing_from_this_package(self) -> None:
        held = (ROOT / "snesdriver" / "errors.py").read_text()

        self.assertEqual(reaching_back(held), [])

    def test_the_reader_of_that_names_an_absolute_import_back(self) -> None:
        found = reaching_back("import snesdriver.windows\n")

        self.assertEqual(found, ["snesdriver.windows"])

    def test_and_a_relative_one(self) -> None:
        found = reaching_back("from . import windows\n")

        self.assertEqual(found, ["."])

    def test_and_steps_over_one_from_outside(self) -> None:
        found = reaching_back(
            "from __future__ import annotations\n"
            "import mapper\n"
            "import mos65xx\n"
            "import snesdrivertools\n"
        )

        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
