import collections
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import executed
from snesdriver import window_for

OBC1 = window_for("obc1", "lorom")

MAIN = bytes.fromhex("a93048ab8df07fad1242ad00218f000070af0000708f00007e8d00106c0090")

DISPATCHED = bytes([0xAD, 0x00, 0x60, 0xCB, 0xDB])

HANDLER = bytes([0x8D, 0xF1, 0x7F, 0x40])

SPINNING = bytes([0x80, 0xFE])


def an_image(program: bytes = MAIN, chipset: int = 0x25) -> bytes:
    rom = bytearray(0x20000)
    rom[0x0000 : len(program)] = program
    rom[0x0100 : 0x0100 + len(DISPATCHED)] = DISPATCHED
    rom[0x0200 : 0x0200 + len(HANDLER)] = HANDLER
    rom[0x1000:0x1002] = (0x8100).to_bytes(2, "little")
    rom[0x7FC0:0x7FD5] = b"EXECUTED CARTRIDGE   "
    rom[0x7FD5] = 0x20
    rom[0x7FD6] = chipset
    rom[0x7FD7] = 0x08
    rom[0x7FDC:0x7FE0] = bytes([0xA5, 0xA5, 0x5A, 0x5A])
    rom[0x7FFA:0x7FFC] = (0x8200).to_bytes(2, "little")
    rom[0x7FFC:0x7FFE] = (0x8000).to_bytes(2, "little")
    return bytes(rom)


def written(image: bytes) -> Path:
    path = Path(tempfile.mkdtemp()) / "executed.sfc"
    path.write_bytes(image)
    return path


class ExecutedTest(unittest.TestCase):
    def test_a_computed_jump_is_followed_into_the_routine_it_names(self) -> None:
        # Arrange
        image = an_image()

        # Act
        _steps, touched = executed.executed(image, OBC1)

        # Assert
        self.assertIn((0x00, 0x8100, 0x306000, "read"), touched)

    def test_an_absolute_access_lands_in_the_bank_the_program_set(self) -> None:
        # Arrange
        image = an_image()

        # Act
        _steps, touched = executed.executed(image, OBC1)

        # Assert
        self.assertIn((0x00, 0x8004, 0x307FF0, "write"), touched)

    def test_a_part_waiting_for_the_frame_is_given_one(self) -> None:
        # Arrange
        image = an_image()

        # Act
        steps, touched = executed.executed(image, OBC1)

        # Assert
        self.assertEqual(
            (steps, sorted(touched)),
            (
                16,
                [
                    (0x00, 0x8004, 0x307FF0, "write"),
                    (0x00, 0x8100, 0x306000, "read"),
                    (0x00, 0x8200, 0x307FF1, "write"),
                ],
            ),
        )

    def test_a_program_that_never_waits_is_still_given_frames(self) -> None:
        # Arrange
        image = an_image(SPINNING)

        # Act
        steps, touched = executed.executed(image, OBC1, budget=executed.NMI_EVERY + 2)

        # Assert
        self.assertEqual(
            (steps, sorted(touched)), (executed.NMI_EVERY + 2, [(0x00, 0x8200, 0x7FF1, "write")])
        )

    def test_the_run_stops_at_its_budget(self) -> None:
        # Arrange
        image = an_image(SPINNING)

        # Act
        steps, touched = executed.executed(image, OBC1, budget=5)

        # Assert
        self.assertEqual((steps, len(touched)), (5, 0))


class ReportTest(unittest.TestCase):
    def test_every_instruction_that_reached_the_part_is_named_with_its_offset(self) -> None:
        # Arrange
        steps, touched = executed.executed(an_image(), OBC1)

        # Act
        lines = executed.report("lorom", steps, touched)

        # Assert
        self.assertEqual(
            lines,
            [
                "  16 instructions run, 3 instructions reached the part",
                "    00:8004 at 0x000004: write 307ff0",
                "    00:8100 at 0x000100: read 306000",
                "    00:8200 at 0x000200: write 307ff1",
            ],
        )

    def test_an_instruction_outside_the_image_has_no_offset(self) -> None:
        # Arrange
        touched = collections.Counter({(0x7E, 0x0000, 0x006000, "write"): 1})

        # Act
        lines = executed.report("lorom", 1, touched)

        # Assert
        self.assertEqual(lines[1], "    7e:0000 at -: write 006000")


class MainTest(unittest.TestCase):
    def test_naming_no_image_prints_the_usage(self) -> None:
        # Arrange
        said = io.StringIO()

        # Act
        with contextlib.redirect_stdout(said):
            code = executed.main([])

        # Assert
        self.assertEqual((code, said.getvalue().strip()), (2, executed.USAGE))

    def test_an_image_with_no_known_part_is_refused(self) -> None:
        # Arrange
        path = written(an_image(chipset=0x02))

        # Act
        with contextlib.redirect_stdout(io.StringIO()):
            code = executed.main([str(path)])

        # Assert
        self.assertEqual(code, 1)

    def test_an_image_with_a_part_is_run_and_reported(self) -> None:
        # Arrange
        path = written(an_image())
        said = io.StringIO()

        # Act
        with contextlib.redirect_stdout(said):
            code = executed.main([str(path), "100"])

        # Assert
        self.assertEqual(
            (code, said.getvalue().splitlines()[:2]),
            (
                0,
                [
                    "  obc1 <Window $00-$3f,$80-$bf:6000 data, 7ff0 status>",
                    "  16 instructions run, 3 instructions reached the part",
                ],
            ),
        )


if __name__ == "__main__":
    unittest.main()
