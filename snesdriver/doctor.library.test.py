import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import cartridges
from snesdriver import doctor


def a_directory(names: tuple[str, ...] = ()) -> Path:
    where = Path(tempfile.mkdtemp())
    for name in names:
        (where / name).write_bytes(b"\x00" * 16)
    return where


class LookingTest(unittest.TestCase):
    def test_a_named_directory_is_reported_and_chosen_even_when_it_is_not_there(self) -> None:
        # Arrange
        environment = {doctor.DIRECTORY_VARIABLE: "/somewhere"}

        # Act
        found = doctor.check_looking(environment)

        # Assert
        self.assertEqual((found[0].detail, found[-1].detail), ("set to /somewhere", "/somewhere"))

    def test_an_unset_variable_says_the_places_are_tried_in_order(self) -> None:
        # Arrange
        alongside, default = a_directory(), a_directory()

        # Act
        found = doctor.check_looking({}, alongside, default)

        # Assert
        self.assertEqual(
            [one.detail for one in found],
            [
                "not set, so the places below are tried in order",
                f"{alongside}, {default}",
                str(alongside),
            ],
        )

    def test_the_real_environment_is_read_when_none_is_given(self) -> None:
        # Arrange
        where = str(a_directory())

        # Act
        with unittest.mock.patch.dict(os.environ, {doctor.DIRECTORY_VARIABLE: where}):
            found = doctor.check_looking()

        # Assert
        self.assertEqual((found[0].detail, found[-1].detail), (f"set to {where}", where))

    def test_the_default_is_chosen_when_no_place_exists(self) -> None:
        # Arrange
        alongside = Path(tempfile.mkdtemp()) / "absent"
        default = Path(tempfile.mkdtemp()) / "absent"

        # Act
        found = doctor.check_looking({}, alongside, default)

        # Assert
        self.assertEqual(found[-1].detail, str(default))

    def test_with_both_places_present_it_chooses_the_one_the_sweep_reads(self) -> None:
        # Arrange
        alongside = a_directory()
        default = a_directory()

        # Act
        found = doctor.check_looking({}, alongside, default)

        # Assert
        self.assertEqual(found[-1].detail, str(cartridges.directory({}, (alongside, default))))


class LibraryTest(unittest.TestCase):
    def test_a_library_that_is_not_there_is_reported_as_absent_not_broken(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "absent"

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertEqual((one.ok, "skip rather than run" in one.detail), (True, True))

    def test_a_library_holding_images_counts_them_and_is_well(self) -> None:
        # Arrange
        where = a_directory(("a.sfc", "b.smc", "c.SFC"))

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertEqual((one.ok, one.detail), (True, f"3 images at {where}"))

    def test_a_directory_that_is_there_and_empty_is_not_well(self) -> None:
        # Arrange
        where = a_directory(("notes.txt",))

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertEqual(
            (one.ok, one.detail), (False, f"{where} is here and holds nothing this package reads")
        )

    def test_the_directory_a_fresh_checkout_ships_empty_is_the_normal_state(self) -> None:
        # Arrange
        where = a_directory(("README.md",))

        # Act
        one = doctor.check_library(where, shipped=where)

        # Assert
        self.assertEqual((one.ok, "skip rather than run" in one.detail), (True, True))

    def test_a_library_that_cannot_be_read_is_reported_as_what_it_said(self) -> None:
        # Arrange
        where = a_directory()

        # Act
        with unittest.mock.patch.object(Path, "rglob", refusing_to_read):
            one = doctor.check_library(where)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, "could not be read: permission denied"))


def refusing_to_read(*_: Any, **__: Any) -> Any:
    raise OSError("permission denied")


if __name__ == "__main__":
    unittest.main()
