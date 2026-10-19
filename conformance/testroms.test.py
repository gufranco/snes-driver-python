import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import testroms

THROUGH_A_DATA_BANK = bytes([0xA9, 0xBF, 0x48, 0xAB, 0xA9, 0x01, 0x8D, 0x00, 0x80, 0xDB])


def an_image(program: bytes = THROUGH_A_DATA_BANK) -> bytes:
    rom = bytearray(0x8000)
    rom[: len(program)] = program
    rom[0x7FFC:0x7FFE] = (0x8000).to_bytes(2, "little")
    return bytes(rom)


class Library:
    def __init__(self, image: bytes | None = None) -> None:
        self.where = Path(tempfile.mkdtemp())
        self.images = self.where / "images"
        self.images.mkdir()
        self.image = an_image() if image is None else image
        (self.images / "made-up.sfc").write_bytes(self.image)
        (self.images / "unlisted.sfc").write_bytes(b"\x00" * 64)
        self.record = self.where / "testroms.json"
        self.record.write_text(
            json.dumps(
                {
                    "cartridges": [
                        {
                            "id": "made-up",
                            "sha256": hashlib.sha256(self.image).hexdigest(),
                            "part": "dsp",
                            "layout": "lorom",
                            "outcome": "read",
                        }
                    ]
                }
            )
        )
        self.measured = self.where / "testroms_measured.json"

    def run(self, *argv: str) -> tuple[int, list[str]]:
        said: list[str] = []
        code = testroms.main(list(argv), said.append, self.record, self.measured)
        return code, said


A_MEASURE = {
    "budget": 100,
    "ran": 6,
    "instructions": 1,
    "dataBanks": ["bf"],
    "longSites": 0,
    "reachedByWalk": 0,
}


class MeasureTest(unittest.TestCase):
    def test_an_access_through_a_data_bank_is_found_by_running_and_missed_by_walking(
        self,
    ) -> None:
        # Arrange
        image = an_image()

        # Act
        found = testroms.measure(image, "dsp", "lorom", 100)

        # Assert
        self.assertEqual(found, A_MEASURE)


class MainTest(unittest.TestCase):
    def test_naming_no_folder_examines_nothing_and_says_so(self) -> None:
        # Arrange
        library = Library()

        # Act
        code, said = library.run()

        # Assert
        self.assertEqual((code, said), (2, ["  0 of 1 test images examined: no folder was named"]))

    def test_recording_writes_what_was_measured(self) -> None:
        # Arrange
        library = Library()

        # Act
        code, _said = library.run(str(library.images), testroms.RECORDING, "100")

        # Assert
        self.assertEqual(
            (code, json.loads(library.measured.read_text())), (0, {"made-up": A_MEASURE})
        )

    def test_a_measure_that_still_holds_passes(self) -> None:
        # Arrange
        library = Library()
        library.run(str(library.images), testroms.RECORDING, "100")

        # Act
        code, said = library.run(str(library.images), "100")

        # Assert
        self.assertEqual((code, said), (0, ["  1 of 1 test images examined"]))

    def test_a_measure_that_moved_fails_and_names_both(self) -> None:
        # Arrange
        library = Library()
        library.measured.write_text(json.dumps({"made-up": {**A_MEASURE, "instructions": 9}}))

        # Act
        code, said = library.run(str(library.images), "100")

        # Assert
        self.assertEqual((code, said[1].startswith("  ! made-up: measured")), (1, True))

    def test_a_folder_holding_none_of_the_images_examines_nothing(self) -> None:
        # Arrange
        library = Library()

        # Act
        code, said = library.run(str(library.where / "absent"))

        # Assert
        self.assertEqual((code, said), (2, ["  0 of 1 test images examined"]))


class RecordedTest(unittest.TestCase):
    def test_the_dsp1_tech_demo_reaches_the_part_only_through_a_data_bank(self) -> None:
        # Arrange
        measured = json.loads(testroms.MEASURED.read_text())

        # Act
        found = measured["dsp1-tech-demo"]

        # Assert
        self.assertEqual(
            (found["instructions"], found["dataBanks"], found["longSites"], found["reachedByWalk"]),
            (48, ["bf"], 0, 0),
        )

    def test_every_measured_image_is_one_the_record_lists(self) -> None:
        # Arrange
        listed = {one["id"] for one in json.loads(testroms.RECORD.read_text())["cartridges"]}

        # Act
        measured = set(json.loads(testroms.MEASURED.read_text()))

        # Assert
        self.assertEqual(measured - listed, set())


class EntryTest(unittest.TestCase):
    def test_it_leaves_with_the_code_the_run_returned(self) -> None:
        # Arrange
        held = sys.argv
        sys.argv = ["testroms"]

        # Act
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
            testroms.entry()
        sys.argv = held

        # Assert
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
