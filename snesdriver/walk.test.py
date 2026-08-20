import sys
import unittest
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesdriver import walk


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


NARROW = (0xE2, 0x20)
WIDE = (0xC2, 0x20)
STORE_LONG = (0x8F, 0x00, 0x80, 0x3F)
LOAD_LONG = (0xAF, 0x00, 0x80, 0x3F)
RETURN = (0x60,)


class WidthTest(unittest.TestCase):
    def test_a_walk_starts_at_the_width_it_was_given(self) -> None:
        steps = list(walk.through(assembled(STORE_LONG, RETURN), 0, narrow=True))

        self.assertTrue(steps[0].narrow)

    def test_narrowing_the_accumulator_is_carried_forward(self) -> None:
        steps = list(walk.through(assembled(NARROW, STORE_LONG, RETURN), 0, narrow=False))

        self.assertTrue(steps[1].narrow)

    def test_and_widening_it_is_too(self) -> None:
        steps = list(walk.through(assembled(WIDE, STORE_LONG, RETURN), 0, narrow=True))

        self.assertFalse(steps[1].narrow)

    def test_a_width_change_that_does_not_touch_the_accumulator_is_ignored(self) -> None:
        code = assembled((0xE2, 0x10), STORE_LONG, RETURN)
        steps = list(walk.through(code, 0, narrow=False))

        self.assertFalse(steps[1].narrow)


class StoppingTest(unittest.TestCase):
    def test_a_walk_stops_where_the_routine_returns(self) -> None:
        steps = list(walk.through(assembled(STORE_LONG, RETURN, STORE_LONG), 0))

        self.assertEqual(len(steps), 2)

    def test_and_where_it_jumps_away(self) -> None:
        steps = list(walk.through(assembled(STORE_LONG, (0x4C, 0x00, 0x80), STORE_LONG), 0))

        self.assertEqual(len(steps), 2)

    def test_a_walk_stops_after_the_number_of_instructions_it_was_allowed(self) -> None:
        code = assembled(*([STORE_LONG] * 40))
        steps = list(walk.through(code, 0, limit=5))

        self.assertEqual(len(steps), 5)

    def test_a_walk_that_runs_off_the_end_stops_there(self) -> None:
        steps = list(walk.through(bytes([0x8F, 0x00]), 0))

        self.assertEqual(steps, [])


class ReachTest(unittest.TestCase):
    def test_a_long_store_reports_the_bank_and_address_it_reaches(self) -> None:
        steps = list(walk.through(assembled(STORE_LONG, RETURN), 0))

        self.assertEqual(steps[0].bank, 0x3F)
        self.assertEqual(steps[0].address, 0x8000)

    def test_a_long_load_is_told_apart_from_a_store(self) -> None:
        steps = list(walk.through(assembled(LOAD_LONG, STORE_LONG, RETURN), 0))

        self.assertTrue(steps[0].reading)
        self.assertFalse(steps[1].reading)

    def test_an_instruction_that_reaches_nowhere_long_says_so(self) -> None:
        steps = list(walk.through(assembled((0xA9, 0x06), RETURN), 0, narrow=True))

        self.assertIsNone(steps[0].bank)

    def test_an_immediate_load_reports_the_value_it_carries(self) -> None:
        steps = list(walk.through(assembled((0xA9, 0x06), RETURN), 0, narrow=True))

        self.assertEqual(steps[0].immediate, 0x06)

    def test_a_wide_immediate_carries_both_of_its_bytes(self) -> None:
        steps = list(walk.through(assembled((0xA9, 0x34, 0x12), RETURN), 0, narrow=False))

        self.assertEqual(steps[0].immediate, 0x1234)

    def test_an_instruction_carrying_no_immediate_says_so(self) -> None:
        steps = list(walk.through(assembled(STORE_LONG, RETURN), 0))

        self.assertIsNone(steps[0].immediate)

    def test_a_step_prints_as_the_instruction_it_stands_for(self) -> None:
        steps = list(walk.through(assembled(STORE_LONG, RETURN), 0))

        self.assertIn("sta", repr(steps[0]))


class AddressTest(unittest.TestCase):
    def test_an_instruction_reaching_nowhere_long_has_no_address(self) -> None:
        steps = list(walk.through(assembled((0xA9, 0x06), RETURN), 0, narrow=True))

        self.assertIsNone(steps[0].address)


class BranchTest(unittest.TestCase):
    def test_a_backward_branch_is_reported_as_a_wait(self) -> None:
        code = assembled(LOAD_LONG, (0x10, 0xFA), RETURN)
        steps = list(walk.through(code, 0))

        self.assertTrue(steps[1].waiting)

    def test_a_forward_branch_is_not(self) -> None:
        code = assembled(LOAD_LONG, (0x10, 0x02), RETURN)
        steps = list(walk.through(code, 0))

        self.assertFalse(steps[1].waiting)

    def test_an_instruction_that_is_not_a_branch_is_not_a_wait(self) -> None:
        steps = list(walk.through(assembled(STORE_LONG, RETURN), 0))

        self.assertFalse(steps[0].waiting)


if __name__ == "__main__":
    unittest.main()
