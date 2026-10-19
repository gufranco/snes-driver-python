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
NARROW = (0xE2, 0x20)
WIDE = (0xC2, 0x20)
STORE_LONG = (0x8F, 0x00, 0x80, 0x3F)
RETURN = (0x60,)
STOP = (0xDB,)
EIGHT_BITS = (True, True)
SIXTEEN_BIT_ACCUMULATOR = (False, True)
UNKNOWN = (None, None)


def image(main: bytes, routine: bytes = b"") -> bytes:
    rom = bytearray(BANK)
    rom[: len(main)] = main
    rom[ROUTINE : ROUTINE + len(routine)] = routine
    rom[RESET : RESET + 2] = (0x8000).to_bytes(2, "little")
    return bytes(rom)


class EntryWidthTest(unittest.TestCase):
    def test_a_routine_is_entered_at_the_width_its_caller_left(self) -> None:
        # Arrange
        rom = image(assembled(WIDE, CALL_ROUTINE, STOP), assembled(STORE_LONG, RETURN))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[ROUTINE], frozenset({SIXTEEN_BIT_ACCUMULATOR}))

    def test_a_routine_two_callers_enter_differently_carries_both_widths(self) -> None:
        # Arrange
        main = assembled(CALL_ROUTINE, WIDE, CALL_ROUTINE, STOP)
        rom = image(main, assembled(STORE_LONG, RETURN))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[ROUTINE], frozenset({EIGHT_BITS, SIXTEEN_BIT_ACCUMULATOR}))

    def test_a_routine_called_twice_alike_carries_one_width(self) -> None:
        # Arrange
        main = assembled(CALL_ROUTINE, CALL_ROUTINE, STORE_LONG, STOP)
        rom = image(main, assembled(STORE_LONG, RETURN))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual((found[ROUTINE], found[6]), (frozenset({EIGHT_BITS}),) * 2)

    def test_the_reset_vector_starts_with_both_registers_eight_bits_wide(self) -> None:
        # Arrange
        rom = image(assembled(STORE_LONG, STOP))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[0], frozenset({EIGHT_BITS}))

    def test_a_walk_from_a_given_entry_knows_neither_width(self) -> None:
        # Arrange
        rom = image(assembled(STORE_LONG, STOP))

        # Act
        found = snesdriver.widths(rom, entry=0x8000)

        # Assert
        self.assertEqual(found[0], frozenset({UNKNOWN}))


class ReturnWidthTest(unittest.TestCase):
    def test_a_caller_resumes_at_the_width_its_callee_returned_with(self) -> None:
        # Arrange
        rom = image(assembled(CALL_ROUTINE, STORE_LONG, STOP), assembled(WIDE, RETURN))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[3], frozenset({SIXTEEN_BIT_ACCUMULATOR}))

    def test_a_callee_returning_two_ways_alike_returns_one_width(self) -> None:
        # Arrange
        routine = assembled((0xF0, 0x01), RETURN, RETURN)
        rom = image(assembled(CALL_ROUTINE, STORE_LONG, STOP), routine)

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[3], frozenset({EIGHT_BITS}))

    def test_a_callee_returning_at_two_widths_returns_both(self) -> None:
        # Arrange
        routine = assembled((0xF0, 0x03), WIDE, RETURN, RETURN)
        rom = image(assembled(CALL_ROUTINE, STORE_LONG, STOP), routine)

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[3], frozenset({EIGHT_BITS, SIXTEEN_BIT_ACCUMULATOR}))

    def test_after_a_callee_never_seen_to_return_neither_width_is_known(self) -> None:
        # Arrange
        rom = image(assembled(CALL_ROUTINE, STORE_LONG, STOP), assembled((0x6C, 0x00, 0x90)))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[3], frozenset({UNKNOWN}))

    def test_after_a_call_through_a_table_neither_width_is_known(self) -> None:
        # Arrange
        rom = image(assembled((0xFC, 0x00, 0x90), STORE_LONG, STOP))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[3], frozenset({UNKNOWN}))

    def test_after_a_call_out_of_the_image_neither_width_is_known(self) -> None:
        # Arrange
        rom = image(assembled((0x22, 0x00, 0x00, 0x7E), STORE_LONG, STOP))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[4], frozenset({UNKNOWN}))

    def test_a_call_at_the_top_of_a_bank_has_nowhere_to_return_to(self) -> None:
        # Arrange
        rom = bytearray(image(b"", assembled(RETURN)))
        rom[0x7FFD:0x8000] = CALL_ROUTINE

        # Act
        found = snesdriver.widths(bytes(rom), entry=0xFFFD)

        # Assert
        self.assertEqual(sorted(found), [ROUTINE, 0x7FFD])


class IndexWidthTest(unittest.TestCase):
    def test_an_index_immediate_of_unknown_width_ends_the_path(self) -> None:
        # Arrange
        rom = image(assembled((0xA2, 0x05), STORE_LONG, STOP))

        # Act
        found = snesdriver.widths(rom, entry=0x8000)

        # Assert
        self.assertEqual(sorted(found), [0])

    def test_a_wide_index_is_carried_into_a_callee(self) -> None:
        # Arrange
        main = assembled((0xC2, 0x10), CALL_ROUTINE, STOP)
        rom = image(main, assembled((0xA2, 0x05, 0x00), STORE_LONG, RETURN))

        # Act
        found = snesdriver.widths(rom)

        # Assert
        self.assertEqual(found[ROUTINE + 3], frozenset({(True, False)}))


class EdgeTest(unittest.TestCase):
    def test_an_entry_below_the_cartridge_reads_nothing(self) -> None:
        # Arrange
        rom = image(assembled(STORE_LONG, STOP))

        # Act
        found = snesdriver.widths(rom, entry=0x0000)

        # Assert
        self.assertEqual(found, {})

    def test_an_instruction_cut_off_by_the_end_of_the_image_reads_nothing(self) -> None:
        # Arrange
        rom = bytearray(image(b""))
        rom[0x7FFF] = 0x8F

        # Act
        found = snesdriver.widths(bytes(rom), entry=0xFFFF)

        # Assert
        self.assertEqual(found, {})

    def test_a_sweep_stops_after_the_number_of_instructions_it_was_allowed(self) -> None:
        # Arrange
        rom = image(assembled(*([(0xEA,)] * 20), STOP))

        # Act
        found = snesdriver.widths(rom, limit=5)

        # Assert
        self.assertEqual(sorted(found), [0, 1, 2, 3, 4])

    def test_the_layout_decides_where_the_vectors_are_read(self) -> None:
        # Arrange
        rom = bytearray(BANK * 2)
        rom[0x8000:0x8005] = assembled(STORE_LONG, STOP)
        rom[0xFFFC:0xFFFE] = (0x8000).to_bytes(2, "little")

        # Act
        found = snesdriver.widths(bytes(rom), "hirom")

        # Assert
        self.assertEqual(found[0x8000], frozenset({EIGHT_BITS}))


class ModuleTest(unittest.TestCase):
    def test_the_sweep_is_reachable_under_the_name_the_readme_gives(self) -> None:
        # Arrange
        rom = image(assembled(STORE_LONG, STOP))

        # Act
        found = snesdriver.sweep.contexts(rom)

        # Assert
        self.assertEqual(found, snesdriver.widths(rom))


if __name__ == "__main__":
    unittest.main()
