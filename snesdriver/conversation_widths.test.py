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
NATIVE_NMI = 0x7FEA
ROUTINE = 0x100
CALL_ROUTINE = (0x20, 0x00, 0x81)
NARROW = (0xE2, 0x20)
WIDE = (0xC2, 0x20)
WIDE_INDEX = (0xC2, 0x10)
NARROW_INDEX = (0xE2, 0x10)
STORE_DATA = (0x8F, 0x00, 0x80, 0x3F)
CALL_THROUGH_A_TABLE = (0xFC, 0x00, 0x90)
SAVE = (0x08,)
RESTORE = (0x28,)
RETURN = (0x60,)
STOP = (0xDB,)
SIXTEEN_BIT_ACCUMULATOR = frozenset({(False, True)})

WINDOW = snesdriver.WINDOWS["dsp"]["lorom"]


def image(main: bytes, routine: bytes = assembled(STORE_DATA, RETURN)) -> bytes:
    rom = bytearray(BANK)
    rom[: len(main)] = main
    rom[ROUTINE : ROUTINE + len(routine)] = routine
    rom[RESET : RESET + 2] = (0x8000).to_bytes(2, "little")
    return bytes(rom)


def unreached(routine: bytes) -> bytes:
    return image(assembled(STOP), routine)


def entered_both_known_and_not() -> bytes:
    rom = bytearray(image(assembled(CALL_ROUTINE, STOP)))
    rom[NATIVE_NMI : NATIVE_NMI + 2] = (0x8100).to_bytes(2, "little")
    return bytes(rom)


class PropagatedWidthTest(unittest.TestCase):
    def test_a_survey_told_the_layout_walks_a_routine_at_the_width_its_caller_left(self) -> None:
        # Arrange
        rom = image(assembled(WIDE, CALL_ROUTINE, STOP))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom")

        # Assert
        self.assertEqual(found, {"write2": 1})

    def test_one_not_told_the_layout_knows_no_width(self) -> None:
        # Arrange
        rom = image(assembled(WIDE, CALL_ROUTINE, STOP))

        # Act
        found = snesdriver.shapes(rom, WINDOW)

        # Assert
        self.assertEqual(found, {"write?": 1})

    def test_a_routine_entered_at_two_widths_has_a_shape_for_each(self) -> None:
        # Arrange
        rom = image(assembled(CALL_ROUTINE, WIDE, CALL_ROUTINE, STOP))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom")

        # Assert
        self.assertEqual(found, {"write1": 1, "write2": 1})

    def test_two_entries_that_give_the_same_shape_count_it_once(self) -> None:
        # Arrange
        rom = image(assembled(CALL_ROUTINE, WIDE_INDEX, CALL_ROUTINE, STOP))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom")

        # Assert
        self.assertEqual(found, {"write1": 1})

    def test_an_entry_of_unknown_width_keeps_its_own_shape(self) -> None:
        # Arrange
        rom = entered_both_known_and_not()

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom")

        # Assert
        self.assertEqual(found, {"write1": 1, "write?": 1})


class RanWidthTest(unittest.TestCase):
    def test_a_routine_the_sweep_never_reached_takes_the_width_a_run_used(self) -> None:
        # Arrange
        rom = unreached(assembled(STORE_DATA, RETURN))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom", ran={ROUTINE: SIXTEEN_BIT_ACCUMULATOR})

        # Assert
        self.assertEqual(found, {"write2*": 1})

    def test_and_says_so_only_until_the_code_sets_the_width_itself(self) -> None:
        # Arrange
        rom = unreached(assembled(STORE_DATA, NARROW, STORE_DATA, RETURN))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom", ran={ROUTINE: SIXTEEN_BIT_ACCUMULATOR})

        # Assert
        self.assertEqual(found, {"write2* write1": 1})

    def test_a_run_settles_only_the_entry_the_sweep_could_not(self) -> None:
        # Arrange
        rom = entered_both_known_and_not()

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom", ran={ROUTINE: SIXTEEN_BIT_ACCUMULATOR})

        # Assert
        self.assertEqual(found, {"write1": 1, "write2*": 1})

    def test_a_run_for_another_instruction_settles_nothing_here(self) -> None:
        # Arrange
        rom = unreached(assembled(STORE_DATA, RETURN))

        # Act
        found = snesdriver.shapes(rom, WINDOW, kind="lorom", ran={0x200: SIXTEEN_BIT_ACCUMULATOR})

        # Assert
        self.assertEqual(found, {"write?": 1})

    def test_a_restored_status_ends_what_the_run_said(self) -> None:
        # Arrange
        code = assembled(STORE_DATA, SAVE, RESTORE, STORE_DATA, RETURN)

        # Act
        found = snesdriver.at(code, 0, WINDOW, narrow=False, index=True, ran=True)

        # Assert
        self.assertEqual(found.shape, "write2* write2")

    def test_a_change_to_the_index_alone_does_not(self) -> None:
        # Arrange
        code = assembled(STORE_DATA, NARROW_INDEX, STORE_DATA, RETURN)

        # Act
        found = snesdriver.at(code, 0, WINDOW, narrow=False, index=True, ran=True)

        # Assert
        self.assertEqual(found.shape, "write2* write2*")

    def test_a_helper_followed_and_back_leaves_what_the_run_said(self) -> None:
        # Arrange
        code = assembled((0x20, 0x0D, 0x80), STORE_DATA, RETURN, bytes(5), RETURN)

        # Act
        found = snesdriver.at(code, 0, WINDOW, narrow=False, index=True, ran=True)

        # Assert
        self.assertEqual(found.shape, "write2*")


class SteppedOverWidthTest(unittest.TestCase):
    def test_after_a_call_it_cannot_follow_a_walk_knows_no_width(self) -> None:
        # Arrange
        code = assembled(STORE_DATA, CALL_THROUGH_A_TABLE, STORE_DATA, RETURN)

        # Act
        found = snesdriver.at(code, 0, WINDOW, narrow=True, index=True)

        # Assert
        self.assertEqual(found.shape, "write1 write?")

    def test_unless_the_sweep_found_one_width_there(self) -> None:
        # Arrange
        code = assembled(STORE_DATA, CALL_THROUGH_A_TABLE, STORE_DATA, RETURN)

        # Act
        found = snesdriver.at(
            code, 0, WINDOW, narrow=True, index=True, known={7: SIXTEEN_BIT_ACCUMULATOR}
        )

        # Assert
        self.assertEqual(found.shape, "write1 write2")

    def test_and_two_widths_there_leave_it_unknown(self) -> None:
        # Arrange
        code = assembled(STORE_DATA, CALL_THROUGH_A_TABLE, STORE_DATA, RETURN)
        both = frozenset({(True, True), (False, True)})

        # Act
        found = snesdriver.at(code, 0, WINDOW, narrow=True, index=True, known={7: both})

        # Assert
        self.assertEqual(found.shape, "write1 write?")

    def test_a_run_width_does_not_outlive_a_call_stepped_over(self) -> None:
        # Arrange
        code = assembled(STORE_DATA, CALL_THROUGH_A_TABLE, STORE_DATA, RETURN)

        # Act
        found = snesdriver.at(
            code, 0, WINDOW, narrow=False, index=True, known={7: SIXTEEN_BIT_ACCUMULATOR}, ran=True
        )

        # Assert
        self.assertEqual(found.shape, "write2* write2")


class IndexTest(unittest.TestCase):
    def test_a_walk_decodes_an_index_immediate_at_the_width_it_was_given(self) -> None:
        # Arrange
        code = assembled(WIDE_INDEX, (0xA2, 0x05, 0x00), STORE_DATA, RETURN)

        # Act
        steps = list(snesdriver.through(code, 0, narrow=True, index=True))

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["rep", "ldx", "sta", "rts"])

    def test_and_ends_at_one_whose_width_it_does_not_know(self) -> None:
        # Arrange
        code = assembled((0xA2, 0x05), STORE_DATA, RETURN)

        # Act
        steps = list(snesdriver.through(code, 0, narrow=True))

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["ldx"])

    def test_a_restored_status_restores_the_index_width_too(self) -> None:
        # Arrange
        code = assembled(SAVE, WIDE_INDEX, RESTORE, (0xA2, 0x05), STORE_DATA, RETURN)

        # Act
        steps = list(snesdriver.through(code, 0, narrow=True, index=True))

        # Assert
        self.assertEqual(steps[4].mnemonic, "sta")


if __name__ == "__main__":
    unittest.main()
