import sys
import unittest
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


BANK = 0x8000
RESET = 0x7FFC
ROUTINE = 0x100
CALL_ROUTINE = (0x20, 0x00, 0x81)
STORE_DATA = (0x8F, 0x00, 0x80, 0x3F)
LOAD_DATA = (0xAF, 0x00, 0x80, 0x3F)
RETURN = (0x60,)
STOP = (0xDB,)

WINDOW = snesdriver.WINDOWS["dsp"]["lorom"]


def image(main: bytes, routine: bytes = assembled(STORE_DATA, RETURN)) -> bytes:
    rom = bytearray(BANK)
    rom[: len(main)] = main
    rom[ROUTINE : ROUTINE + len(routine)] = routine
    rom[RESET : RESET + 2] = (0x8000).to_bytes(2, "little")
    return bytes(rom)


class TracedWidthTest(unittest.TestCase):
    def test_an_access_of_unknown_width_takes_the_width_a_trace_saw_there(self) -> None:
        # Arrange
        rom = image(assembled(STOP))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom", traced={ROUTINE: 2})

        # Assert
        self.assertEqual(found, {"write2~": 1})

    def test_a_width_the_code_sets_is_kept_whatever_a_trace_saw(self) -> None:
        # Arrange
        rom = image(assembled(CALL_ROUTINE, STOP))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom", traced={ROUTINE: 2})

        # Assert
        self.assertEqual(found, {"write1": 1})

    def test_a_trace_of_another_instruction_settles_nothing_here(self) -> None:
        # Arrange
        rom = image(assembled(STOP))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom", traced={ROUTINE + 4: 2})

        # Assert
        self.assertEqual(found, {"write?": 1})

    def test_each_access_is_settled_by_its_own_site_alone(self) -> None:
        # Arrange
        code = assembled(STORE_DATA, LOAD_DATA, RETURN)

        # Act
        found = snesdriver.at(code, 0, WINDOW, traced={4: 1})

        # Assert
        self.assertEqual(found.shape, "write? read1~")

    def test_a_traced_width_is_counted_in_the_bytes_moved(self) -> None:
        # Arrange
        code = assembled(STORE_DATA, LOAD_DATA, RETURN)

        # Act
        found = snesdriver.at(code, 0, WINDOW, traced={0: 2, 4: 1})

        # Assert
        self.assertEqual((found.written, found.read), (2, 1))


if __name__ == "__main__":
    unittest.main()
