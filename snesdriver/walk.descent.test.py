import sys
import unittest
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


RETURN = (0x60,)
STORE_PART = (0x8D, 0x00, 0x38)
LOAD_PART = (0xAD, 0x04, 0x38)
NOTHING = (0xEA,)
HELPER_AT = 0x10
CALLER = assembled((0x20, 0x10, 0x80), STORE_PART, RETURN)


def calling(helper: "Iterable[int]", caller: bytes = CALLER) -> bytes:
    return caller + bytes(HELPER_AT - len(caller)) + bytes(helper)


def walked(code: bytes, **options: Any) -> list[Any]:
    return list(snesdriver.through(code, 0, **options))


def depths(code: bytes, **options: Any) -> list[int]:
    return [step.depth for step in walked(code, **options)]


STEPPED_OVER = [0, 0, 0]

FOLLOWED = [0, 1, 1, 0, 0]


class DescentTest(unittest.TestCase):
    def test_a_walk_reads_what_a_helper_reaches_and_comes_back(self) -> None:
        # Arrange
        code = calling(assembled(LOAD_PART, RETURN))

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual(
            [(step.mnemonic, step.address, step.offset) for step in steps],
            [
                ("jsr", None, 0),
                ("lda", 0x3804, 0x10),
                ("rts", None, 0x13),
                ("sta", 0x3800, 3),
                ("rts", None, 6),
            ],
        )

    def test_an_instruction_inside_a_helper_says_how_deep_it_is(self) -> None:
        # Arrange
        code = calling(assembled(LOAD_PART, RETURN))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, FOLLOWED)

    def test_a_walk_does_not_descend_past_the_depth_it_was_given(self) -> None:
        # Arrange
        code = calling(assembled(LOAD_PART, RETURN))

        # Act
        found = depths(code, depth=0)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_helper_that_runs_long_does_not_spend_the_caller_budget(self) -> None:
        # Arrange
        code = calling(assembled(*([NOTHING] * 40), LOAD_PART, RETURN))

        # Act
        steps = walked(code, limit=3)

        # Assert
        self.assertEqual(
            [step.mnemonic for step in steps if step.depth == 0], ["jsr", "sta", "rts"]
        )

    def test_a_descent_that_never_ends_stops_at_sixteen_times_the_limit(self) -> None:
        # Arrange
        code = calling(assembled(*([NOTHING] * 40), LOAD_PART, RETURN))

        # Act
        steps = walked(code, limit=2)

        # Assert
        self.assertEqual(len(steps), 16 * 2)

    def test_a_call_stays_in_the_bank_it_was_made_from(self) -> None:
        # Arrange
        decoy = calling(assembled(LOAD_PART, RETURN))
        helper = calling((0xAD, 0x02, 0x38, 0x60))
        code = decoy + bytes(0x8000 - len(decoy)) + helper + bytes(0x8000 - len(helper))

        # Act
        steps = list(snesdriver.through(code, 0x8000))

        # Assert
        self.assertEqual((steps[1].offset, steps[1].bank, steps[1].address), (0x8010, 1, 0x3802))

    def test_a_long_call_carries_the_bank_it_goes_to(self) -> None:
        # Arrange
        rom = bytearray(0x18000)
        rom[0:8] = assembled((0x22, 0x00, 0x90, 0x02), STORE_PART, RETURN)
        rom[0x11000:0x11004] = assembled(LOAD_PART, RETURN)

        # Act
        steps = walked(bytes(rom))

        # Assert
        self.assertEqual((steps[1].offset, steps[1].bank, steps[1].depth), (0x11000, 0x02, 1))


class SteppedOverTest(unittest.TestCase):
    def test_a_call_into_a_software_break_is_stepped_over(self) -> None:
        # Arrange
        code = calling((0x00, 0x00, 0x60))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_call_into_a_coprocessor_break_is_stepped_over(self) -> None:
        # Arrange
        code = calling((0x02, 0x00, 0x60))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_call_into_a_reserved_opcode_is_stepped_over(self) -> None:
        # Arrange
        code = calling((0x42, 0x00, 0x60))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_call_into_a_helper_that_loops_forever_is_stepped_over(self) -> None:
        # Arrange
        code = calling((0x80, 0xFE))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_call_into_a_helper_that_leaves_by_an_interrupt_return_is_stepped_over(self) -> None:
        # Arrange
        code = calling((0x40,))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_call_into_a_helper_that_runs_off_the_image_is_stepped_over(self) -> None:
        # Arrange
        code = calling((0xAF, 0x00))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_call_into_a_place_the_image_does_not_hold_is_stepped_over(self) -> None:
        # Arrange
        code = assembled((0x22, 0x00, 0x80, 0x7E), STORE_PART, RETURN)

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_an_indirect_call_is_stepped_over_because_its_target_cannot_be_read(self) -> None:
        # Arrange
        caller = assembled((0xFC, 0x10, 0x80), STORE_PART, RETURN)
        code = calling(assembled(LOAD_PART, RETURN), caller)

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_helper_that_jumps_away_is_stepped_over(self) -> None:
        # Arrange
        code = calling(assembled((0x5C, 0x00, 0x80, 0x7E), RETURN))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_helper_that_runs_past_the_top_of_a_bank_is_stepped_over(self) -> None:
        # Arrange
        rom = bytearray(0x8000)
        rom[0:7] = assembled((0x20, 0xFF, 0xFF), STORE_PART, RETURN)
        rom[0x7FFF] = 0xEA

        # Act
        found = depths(bytes(rom))

        # Assert
        self.assertEqual(found, STEPPED_OVER)


class ReturningTest(unittest.TestCase):
    def test_a_helper_whose_jump_lands_on_a_return_is_followed_back_to_the_caller(self) -> None:
        # Arrange
        code = calling(assembled((0x4C, 0x16, 0x80), (0xAD, 0x02, 0x38), RETURN))

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual(
            [(step.mnemonic, step.offset, step.depth) for step in steps],
            [("jsr", 0, 0), ("jmp", 0x10, 1), ("rts", 0x16, 1), ("sta", 3, 0), ("rts", 6, 0)],
        )

    def test_a_helper_that_branches_always_is_followed_back_to_the_caller(self) -> None:
        # Arrange
        code = calling(assembled((0x80, 0x03), (0xAD, 0x02, 0x38), RETURN))

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual([step.depth for step in steps], [0, 1, 1, 0, 0])

    def test_a_long_jump_inside_a_helper_carries_the_bank_it_names(self) -> None:
        # Arrange
        rom = bytearray(0x10000)
        rom[0:7] = CALLER
        rom[0x10:0x14] = (0x5C, 0x00, 0x90, 0x01)
        rom[0x9000:0x9004] = assembled(LOAD_PART, RETURN)

        # Act
        steps = walked(bytes(rom))

        # Assert
        self.assertEqual(
            [(step.offset, step.bank, step.depth) for step in steps[1:4]],
            [(0x10, 0x01, 1), (0x9000, 0x01, 1), (0x9003, None, 1)],
        )

    def test_a_helper_that_returns_within_two_hundred_instructions_is_followed(self) -> None:
        # Arrange
        code = calling(assembled(*([NOTHING] * 199), RETURN))

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual(sum(1 for step in steps if step.depth == 1), 200)

    def test_and_one_that_takes_a_two_hundred_and_first_is_stepped_over(self) -> None:
        # Arrange
        code = calling(assembled(*([NOTHING] * 200), RETURN))

        # Act
        found = depths(code)

        # Assert
        self.assertEqual(found, STEPPED_OVER)

    def test_a_long_return_ends_a_helper_too(self) -> None:
        # Arrange
        code = calling((0x6B,))

        # Act
        steps = walked(code)

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["jsr", "rtl", "sta", "rts"])


class NarrowedInsideAHelperTest(unittest.TestCase):
    def test_an_interrupt_return_the_narrowed_helper_reaches_ends_the_walk(self) -> None:
        # Arrange
        code = calling((0xE2, 0x20, 0xA9, 0xEA, 0x40, 0x60))

        # Act
        steps = walked(code, narrow=False)

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["jsr", "sep", "lda", "rti"])

    def test_an_indirect_jump_the_narrowed_helper_reaches_ends_the_walk(self) -> None:
        # Arrange
        code = calling((0xE2, 0x20, 0xA9, 0xEA, 0x6C, 0xEA, 0xEA, 0x60))

        # Act
        steps = walked(code, narrow=False)

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["jsr", "sep", "lda", "jmp"])

    def test_a_jump_out_of_the_image_the_narrowed_helper_reaches_ends_the_walk(self) -> None:
        # Arrange
        code = calling((0xE2, 0x20, 0xA9, 0xEA, 0x4C, 0xEA, 0x1A, 0x60))

        # Act
        steps = walked(code, narrow=False)

        # Assert
        self.assertEqual([step.mnemonic for step in steps], ["jsr", "sep", "lda", "jmp"])


if __name__ == "__main__":
    unittest.main()
