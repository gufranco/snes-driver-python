import sys
import unittest
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


def walked(code: bytes, **options: Any) -> list[Any]:
    return list(snesdriver.through(code, 0, **options))


NARROW = (0xE2, 0x20)
WIDE = (0xC2, 0x20)
STORE_LONG = (0x8F, 0x00, 0x80, 0x3F)
LOAD_LONG = (0xAF, 0x00, 0x80, 0x3F)
RETURN = (0x60,)
STORE_PART = (0x8D, 0x00, 0x38)
LOAD_PART = (0xAD, 0x04, 0x38)
NOTHING = (0xEA,)


class WidthTest(unittest.TestCase):
    def test_a_walk_starts_at_the_width_it_was_given(self) -> None:
        # Arrange
        code = assembled(STORE_LONG, RETURN)

        # Act
        steps = walked(code, narrow=True)

        # Assert
        self.assertEqual((steps[0].narrow, steps[0].width), (True, 1))

    def test_narrowing_the_accumulator_is_carried_forward(self) -> None:
        # Arrange
        code = assembled(NARROW, STORE_LONG, RETURN)

        # Act
        steps = walked(code, narrow=False)

        # Assert
        self.assertEqual((steps[1].narrow, steps[1].width), (True, 1))

    def test_and_widening_it_is_too(self) -> None:
        # Arrange
        code = assembled(WIDE, STORE_LONG, RETURN)

        # Act
        steps = walked(code, narrow=True)

        # Assert
        self.assertEqual((steps[1].narrow, steps[1].width), (False, 2))

    def test_a_width_change_that_does_not_touch_the_accumulator_is_ignored(self) -> None:
        # Arrange
        code = assembled((0xE2, 0x10), STORE_LONG, RETURN)

        # Act
        steps = walked(code, narrow=False)

        # Assert
        self.assertEqual(steps[1].width, 2)


class StoppingTest(unittest.TestCase):
    def test_a_walk_stops_where_the_routine_returns(self) -> None:
        # Arrange
        code = assembled(STORE_LONG, RETURN, STORE_LONG)

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["sta", "rts"])

    def test_and_where_it_jumps_away(self) -> None:
        # Arrange
        code = assembled(STORE_LONG, (0x4C, 0x00, 0x80), STORE_LONG)

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["sta", "jmp"])

    def test_a_walk_stops_at_an_interrupt_return(self) -> None:
        # Arrange
        code = assembled((0x40,), STORE_LONG, RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["rti"])

    def test_a_walk_stops_after_the_number_of_instructions_it_was_allowed(self) -> None:
        # Arrange
        code = assembled(*([STORE_LONG] * 40))

        # Act
        steps = walked(code, limit=5)

        # Assert
        self.assertEqual(len(steps), 5)

    def test_the_default_allowance_is_the_one_the_readme_gives(self) -> None:
        # Arrange
        code = assembled(*([NOTHING] * 200))

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual((len(steps), snesdriver.DEFAULT_LIMIT), (80, 80))

    def test_a_walk_that_runs_off_the_end_stops_there(self) -> None:
        # Arrange
        code = bytes([0x8F, 0x00])

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual(steps, [])


class ReachTest(unittest.TestCase):
    def test_a_long_store_reports_the_bank_and_address_it_reaches(self) -> None:
        # Arrange
        code = assembled(STORE_LONG, RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual((steps[0].bank, steps[0].address, steps[0].banked), (0x3F, 0x8000, True))

    def test_an_absolute_store_reaches_the_bank_the_routine_runs_in(self) -> None:
        # Arrange
        code = assembled(STORE_PART, RETURN)

        # Act
        steps = walked(code, bank=0x12)

        # Assert
        self.assertEqual((steps[0].bank, steps[0].address, steps[0].banked), (0x12, 0x3800, False))

    def test_the_bank_defaults_to_the_one_the_offset_sits_in(self) -> None:
        # Arrange
        code = bytes(0x10000) + assembled(STORE_PART, RETURN)

        # Act
        steps = list(snesdriver.through(code, 0x10000))

        # Assert
        self.assertEqual(steps[0].bank, 0x02)

    def test_a_long_load_is_told_apart_from_a_store(self) -> None:
        # Arrange
        code = assembled(LOAD_LONG, STORE_LONG, RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual([step.reading for step in steps[:2]], [True, False])

    def test_an_instruction_that_reaches_nowhere_says_so(self) -> None:
        # Arrange
        code = assembled((0xA9, 0x06), RETURN)

        # Act
        steps = walked(code, narrow=True)

        # Assert
        self.assertEqual((steps[0].bank, steps[0].address), (None, None))

    def test_an_immediate_load_reports_the_value_it_carries(self) -> None:
        # Arrange
        code = assembled((0xA9, 0x06), RETURN)

        # Act
        steps = walked(code, narrow=True)

        # Assert
        self.assertEqual(steps[0].immediate, 0x06)

    def test_a_wide_immediate_carries_both_of_its_bytes(self) -> None:
        # Arrange
        code = assembled((0xA9, 0x34, 0x12), RETURN)

        # Act
        steps = walked(code, narrow=False)

        # Assert
        self.assertEqual(steps[0].immediate, 0x1234)

    def test_an_instruction_carrying_no_immediate_says_so(self) -> None:
        # Arrange
        code = assembled(STORE_LONG, RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertIsNone(steps[0].immediate)

    def test_a_step_prints_as_the_instruction_it_stands_for(self) -> None:
        # Arrange
        code = assembled(STORE_LONG, RETURN)

        # Act
        printed = repr(walked(code)[0])

        # Assert
        self.assertEqual(printed, "<Step sta $3f8000 byte>")

    def test_and_says_when_it_moves_a_word(self) -> None:
        # Arrange
        code = assembled(STORE_LONG, RETURN)

        # Act
        printed = repr(walked(code, narrow=False)[0])

        # Assert
        self.assertEqual(printed, "<Step sta $3f8000 word>")

    def test_a_branch_lands_relative_to_the_address_given(self) -> None:
        # Arrange
        code = assembled((0x80, 0x02))

        # Act
        steps = walked(code, address=0x9000)

        # Assert
        self.assertEqual(repr(steps[0]), "<Step bra $9004 byte>")

    def test_and_the_address_defaults_to_the_offset_in_a_low_bank(self) -> None:
        # Arrange
        code = bytes(0x8010) + assembled((0x80, 0x02))

        # Act
        steps = list(snesdriver.through(code, 0x8010))

        # Assert
        self.assertEqual(repr(steps[0]), "<Step bra $8014 byte>")


class BranchTest(unittest.TestCase):
    def test_a_backward_branch_is_reported_as_a_wait(self) -> None:
        # Arrange
        code = assembled(LOAD_LONG, (0x10, 0xFA), RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertTrue(steps[1].waiting)

    def test_a_forward_branch_is_not(self) -> None:
        # Arrange
        code = assembled(LOAD_LONG, (0x10, 0x02), RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertFalse(steps[1].waiting)

    def test_an_instruction_that_is_not_a_branch_is_not_a_wait(self) -> None:
        # Arrange
        code = assembled(STORE_LONG, RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertFalse(steps[0].waiting)

    def test_a_long_branch_backwards_is_a_wait(self) -> None:
        # Arrange
        code = assembled((0x82, 0xFD, 0xFF))

        # Act
        steps = walked(code)

        # Assert
        self.assertTrue(steps[0].waiting)

    def test_a_long_branch_forwards_is_not_a_wait(self) -> None:
        # Arrange
        code = assembled((0x82, 0x00, 0x01))

        # Act
        steps = walked(code)

        # Assert
        self.assertFalse(steps[0].waiting)


class NotMemoryTest(unittest.TestCase):
    def test_pushing_a_constant_reaches_nothing(self) -> None:
        # Arrange
        code = assembled((0xF4, 0x00, 0x38), RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual((steps[0].bank, steps[0].address), (None, None))

    def test_pushing_a_computed_address_reaches_nothing(self) -> None:
        # Arrange
        code = assembled((0x62, 0x00, 0x38), RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual((steps[0].bank, steps[0].address), (None, None))

    def test_a_load_at_the_same_address_still_reaches_it(self) -> None:
        # Arrange
        code = assembled(LOAD_PART, RETURN)

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual((steps[0].bank, steps[0].address), (0x00, 0x3804))


if __name__ == "__main__":
    unittest.main()
