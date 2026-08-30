import sys
import unittest
from collections.abc import Iterable
from pathlib import Path
from typing import Any

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


def image(body: bytes, vector: int = 0x8000, banks: int = 1) -> bytes:
    rom = bytearray(0x8000 * banks)
    rom[: len(body)] = body
    rom[0x7FFC:0x7FFE] = vector.to_bytes(2, "little")
    return bytes(rom)


STORE_PART = (0x8D, 0x00, 0x38)
LOAD_PART = (0xAD, 0x04, 0x38)
CALL = (0x20, 0x10, 0x80)
JUMP = (0x4C, 0x14, 0x80)
IF_EQUAL = (0xF0, 0x02)
FILLER = (0xEA,)
STORE_LONG_PART = (0x8F, 0x02, 0x38, 0x00)

BRANCHING = assembled(
    STORE_PART, CALL, IF_EQUAL, RETURN, FILLER, LOAD_PART, JUMP, STORE_LONG_PART, RETURN
)
"""A routine whose only read of the part sits on the taken side of a branch, and
whose only long access sits inside a call. A straight walk reaches neither.
"""


class SweepTest(unittest.TestCase):
    def test_a_sweep_starts_at_the_reset_vector(self) -> None:
        steps = list(walk.everywhere(image(BRANCHING)))

        self.assertEqual(steps[0].offset, 0x0000)

    def test_a_sweep_starts_where_it_is_told_instead(self) -> None:
        steps = list(walk.everywhere(image(BRANCHING), 0x8010))

        self.assertEqual(steps[0].mnemonic, "sta")

    def test_a_sweep_takes_the_side_a_branch_jumps_to(self) -> None:
        steps = list(walk.everywhere(image(BRANCHING)))

        self.assertIn(0x000A, [step.offset for step in steps])

    def test_a_sweep_takes_the_side_a_branch_falls_through_to(self) -> None:
        steps = list(walk.everywhere(image(BRANCHING)))

        self.assertIn(0x0008, [step.offset for step in steps])

    def test_a_sweep_follows_a_call(self) -> None:
        steps = list(walk.everywhere(image(BRANCHING)))

        self.assertIn(0x0010, [step.offset for step in steps])

    def test_a_sweep_decodes_nothing_control_flow_never_arrives_at(self) -> None:
        steps = list(walk.everywhere(image(BRANCHING)))

        self.assertNotIn(0x0009, [step.offset for step in steps])

    def test_a_sweep_reads_each_address_once(self) -> None:
        steps = list(walk.everywhere(image(assembled((0x4C, 0x00, 0x80)))))

        self.assertEqual(len(steps), 1)

    def test_a_sweep_stops_at_the_limit_it_is_given(self) -> None:
        steps = list(walk.everywhere(image(BRANCHING), limit=1))

        self.assertEqual(len(steps), 1)

    def test_a_sweep_reads_nothing_below_the_cartridge(self) -> None:
        steps = list(walk.everywhere(image(BRANCHING), 0x0000))

        self.assertEqual(steps, [])

    def test_a_sweep_stops_where_the_image_runs_out(self) -> None:
        rom = bytearray(image(assembled((0x5C, 0xFF, 0xFF, 0x01)), banks=2))
        rom[0xFFFF] = 0xAF

        steps = list(walk.everywhere(bytes(rom)))

        self.assertEqual([step.mnemonic for step in steps], ["jml"])

    def test_a_sweep_stops_at_the_top_of_a_bank(self) -> None:
        rom = bytearray(image(assembled((0x5C, 0xFF, 0xFF, 0x01)), banks=2))
        rom[0xFFFF] = 0xEA

        steps = list(walk.everywhere(bytes(rom)))

        self.assertEqual([step.mnemonic for step in steps], ["jml", "nop"])

    def test_a_sweep_carries_a_narrowed_accumulator_across_a_branch(self) -> None:
        rom = image(assembled(NARROW, IF_EQUAL, RETURN, FILLER, STORE_LONG_PART, RETURN))

        steps = list(walk.everywhere(rom))

        self.assertTrue(steps[-2].narrow)

    def test_a_sweep_carries_a_widened_index_across_a_branch(self) -> None:
        rom = image(assembled((0xC2, 0x10), IF_EQUAL, RETURN, FILLER, (0xA0, 0x34, 0x12), RETURN))

        steps = list(walk.everywhere(rom))

        self.assertEqual(steps[-2].one.size, 3)

    def test_a_sweep_does_not_follow_a_jump_out_of_the_image(self) -> None:
        steps = list(walk.everywhere(image(assembled((0x5C, 0x00, 0x80, 0x7E), RETURN))))

        self.assertEqual([step.mnemonic for step in steps], ["jml"])


class PlaceTest(unittest.TestCase):
    def test_an_address_below_the_window_is_kept_nowhere(self) -> None:
        self.assertIsNone(walk._offset(0x00, 0x7FFF, 1))

    def test_a_bank_the_image_does_not_have_is_kept_nowhere(self) -> None:
        self.assertIsNone(walk._offset(0x02, 0x8000, 2))

    def test_a_mirrored_bank_is_the_same_place_as_the_bank_it_mirrors(self) -> None:
        self.assertEqual(walk._offset(0x81, 0x8000, 2), walk._offset(0x01, 0x8000, 2))


class TargetTest(unittest.TestCase):
    def only(self, *chunks: "Iterable[int]") -> Any:
        return next(iter(walk.through(assembled(*chunks), 0))).one

    def test_an_instruction_that_sends_control_nowhere_has_no_target(self) -> None:
        self.assertIsNone(walk._target(self.only(STORE_LONG_PART), 0x00))

    def test_an_instruction_with_no_operand_has_no_target(self) -> None:
        self.assertIsNone(walk._target(self.only(RETURN), 0x00))

    def test_an_indirect_jump_has_no_target_that_can_be_read(self) -> None:
        self.assertIsNone(walk._target(self.only((0x6C, 0x00, 0x80)), 0x00))

    def test_a_call_stays_in_the_bank_it_was_made_from(self) -> None:
        self.assertEqual(walk._target(self.only(CALL), 0x12), (0x12, 0x8010))

    def test_a_long_call_carries_the_bank_it_goes_to(self) -> None:
        found = walk._target(self.only((0x22, 0x00, 0x90, 0x02)), 0x12)

        self.assertEqual(found, (0x02, 0x9000))

    def test_a_forward_branch_resolves_past_the_instruction(self) -> None:
        self.assertEqual(walk._target(self.only(IF_EQUAL), 0x00), (0x00, 0x8004))

    def test_a_backward_branch_resolves_before_the_instruction(self) -> None:
        self.assertEqual(walk._target(self.only((0xF0, 0xFC)), 0x00), (0x00, 0x7FFE))

    def test_a_long_branch_resolves_by_two_bytes_of_displacement(self) -> None:
        found = walk._target(self.only((0x82, 0x00, 0x01)), 0x00)

        self.assertEqual(found, (0x00, 0x8103))

    def test_a_backward_long_branch_resolves_before_the_instruction(self) -> None:
        found = walk._target(self.only((0x82, 0xFD, 0xFF)), 0x00)

        self.assertEqual(found, (0x00, 0x8000))


class LongBranchTest(unittest.TestCase):
    def test_a_long_branch_backwards_is_a_wait(self) -> None:
        steps = list(walk.through(assembled((0x82, 0xFD, 0xFF)), 0))

        self.assertTrue(steps[0].waiting)

    def test_a_long_branch_forwards_is_not_a_wait(self) -> None:
        steps = list(walk.through(assembled((0x82, 0x00, 0x01)), 0))

        self.assertFalse(steps[0].waiting)


HELPER = (0xAD, 0x04, 0x38, 0x60)
PUSH_CONSTANT = (0xF4, 0x00, 0x38)
PUSH_RELATIVE = (0x62, 0x00, 0x38)


def calling(helper: bytes, after: bytes) -> bytes:
    """A routine that calls a helper laid out after it, then runs `after`.

    The call and its destination are built together because they have to agree:
    a target one byte off lands mid-instruction and decodes as something else.
    """
    body = bytearray((0x20, 0x00, 0x00))
    body += after
    at = 0x8000 + len(body)
    body[1], body[2] = at & 0xFF, at >> 8
    return bytes(body) + helper


THROUGH_A_HELPER = calling(assembled(HELPER), assembled(STORE_PART, RETURN))
"""Call a helper that reads the part, then store to it and return.

A walk that stopped at the call saw neither access; one that stepped over the
call saw only the store.
"""


class DescentTest(unittest.TestCase):
    def test_a_walk_reads_what_a_helper_reaches(self) -> None:
        steps = list(walk.through(THROUGH_A_HELPER, 0))

        self.assertIn("lda $3804", [step.one.text for step in steps])

    def test_and_comes_back_for_what_the_caller_reaches_after_it(self) -> None:
        steps = list(walk.through(THROUGH_A_HELPER, 0))

        self.assertEqual([step.one.text for step in steps][-2:], ["sta $3800", "rts"])

    def test_an_instruction_inside_a_helper_says_how_deep_it_is(self) -> None:
        steps = list(walk.through(THROUGH_A_HELPER, 0))

        self.assertEqual([step.depth for step in steps], [0, 1, 1, 0, 0])

    def test_a_walk_does_not_descend_past_the_depth_it_was_given(self) -> None:
        steps = list(walk.through(THROUGH_A_HELPER, 0, depth=0))

        self.assertNotIn("lda $3804", [step.one.text for step in steps])

    def test_a_call_into_something_that_never_returns_is_stepped_over(self) -> None:
        code = calling(bytes((0xEA, 0x00)), assembled(STORE_PART, RETURN))

        steps = list(walk.through(code, 0))

        self.assertEqual([step.depth for step in steps], [0, 0, 0])

    def test_a_call_into_a_helper_that_loops_forever_is_stepped_over(self) -> None:
        code = calling(bytes((0x80, 0xFE)), assembled(STORE_PART, RETURN))

        steps = list(walk.through(code, 0))

        self.assertEqual([step.depth for step in steps], [0, 0, 0])

    def test_a_call_into_a_place_the_image_does_not_hold_is_stepped_over(self) -> None:
        code = assembled((0x22, 0x00, 0x80, 0x7E), STORE_PART, RETURN)

        steps = list(walk.through(code, 0))

        self.assertEqual([step.depth for step in steps], [0, 0, 0])

    def test_a_helper_that_runs_long_does_not_spend_the_caller_budget(self) -> None:
        helper = assembled(*([(0xEA,)] * 40), HELPER)
        code = calling(helper, assembled(STORE_PART, RETURN))

        steps = list(walk.through(code, 0, limit=3))

        self.assertIn("sta $3800", [step.one.text for step in steps])

    def test_a_descent_that_never_ends_stops_at_the_second_bound(self) -> None:
        helper = assembled(*([(0xEA,)] * 40), HELPER)
        code = calling(helper, assembled(STORE_PART, RETURN))

        steps = list(walk.through(code, 0, limit=1))

        self.assertLessEqual(len(steps), walk.DESCENT_ROOM)


class NotMemoryTest(unittest.TestCase):
    def test_pushing_a_constant_reaches_no_address(self) -> None:
        steps = list(walk.through(assembled(PUSH_CONSTANT, RETURN), 0))

        self.assertIsNone(steps[0].address)

    def test_and_names_no_bank_either(self) -> None:
        steps = list(walk.through(assembled(PUSH_CONSTANT, RETURN), 0))

        self.assertIsNone(steps[0].bank)

    def test_pushing_a_computed_address_reaches_no_address(self) -> None:
        steps = list(walk.through(assembled(PUSH_RELATIVE, RETURN), 0))

        self.assertIsNone(steps[0].address)

    def test_a_load_at_the_same_address_still_reaches_it(self) -> None:
        steps = list(walk.through(assembled(LOAD_PART, RETURN), 0))

        self.assertEqual(steps[0].address, 0x3804)


class ReturnsTest(unittest.TestCase):
    def test_a_routine_that_returns_is_followed(self) -> None:
        self.assertTrue(walk._returns(assembled(HELPER), (0x00, 0x8000), True, 1))

    def test_a_routine_that_reads_as_data_is_not(self) -> None:
        self.assertFalse(walk._returns(assembled((0x00, 0xB7), RETURN), (0x00, 0x8000), True, 1))

    def test_a_routine_running_off_the_image_is_not(self) -> None:
        self.assertFalse(walk._returns(assembled((0xAF, 0x00)), (0x00, 0x8000), True, 1))

    def test_a_destination_the_image_does_not_hold_is_not(self) -> None:
        self.assertFalse(walk._returns(assembled(HELPER), (0x00, 0x0000), True, 1))

    def test_a_jump_that_lands_on_a_return_is_followed(self) -> None:
        code = assembled((0x4C, 0x04, 0x80), (0xEA,), RETURN)

        self.assertTrue(walk._returns(code, (0x00, 0x8000), True, 1))

    def test_a_jump_out_of_the_image_is_not(self) -> None:
        code = assembled((0x5C, 0x00, 0x80, 0x7E), RETURN)

        self.assertFalse(walk._returns(code, (0x00, 0x8000), True, 1))

    def test_a_routine_that_runs_past_the_top_of_a_bank_is_not(self) -> None:
        rom = bytearray(0x8000)
        rom[0x7FFF] = 0xEA

        self.assertFalse(walk._returns(bytes(rom), (0x00, 0xFFFF), True, 1))

    def test_a_routine_longer_than_the_probe_allows_is_not(self) -> None:
        code = assembled(*([(0xEA,)] * (walk.PROBE_LIMIT + 4)), RETURN)

        self.assertFalse(walk._returns(code, (0x00, 0x8000), True, 1))


def vectored(body: bytes, **vectors: int) -> bytes:
    """An image whose named vectors point where a test wants them to."""
    rom = bytearray(0x8000)
    rom[: len(body)] = body
    for name, address in vectors.items():
        at = getattr(walk, name)
        rom[at : at + 2] = address.to_bytes(2, "little")
    return bytes(rom)


class EntryTest(unittest.TestCase):
    def test_a_sweep_reads_every_vector_a_cartridge_publishes(self) -> None:
        rom = vectored(assembled(STORE_PART, RETURN, LOAD_PART, RETURN))
        held = bytearray(rom)
        held[0x7FEA:0x7FEC] = (0x8004).to_bytes(2, "little")
        held[0x7FFC:0x7FFE] = (0x8000).to_bytes(2, "little")

        found = {step.offset for step in walk.everywhere(bytes(held))}

        self.assertEqual(sorted(found), [0x0000, 0x0003, 0x0004, 0x0007])

    def test_a_vector_pointing_below_the_cartridge_is_not_a_start(self) -> None:
        rom = bytearray(vectored(assembled(STORE_PART, RETURN)))
        rom[0x7FEA:0x7FEC] = (0x0100).to_bytes(2, "little")
        rom[0x7FFC:0x7FFE] = (0x8000).to_bytes(2, "little")

        found = list(walk.everywhere(bytes(rom)))

        self.assertEqual([step.offset for step in found], [0x0000, 0x0003])

    def test_two_vectors_naming_one_address_start_it_once(self) -> None:
        found = walk._entries(vectored(assembled(RETURN), RESET_VECTOR=0x8000), None, 1)

        self.assertEqual(found.count(0x8000), 1)

    def test_a_named_entry_is_the_only_one_a_sweep_uses(self) -> None:
        rom = vectored(assembled(STORE_PART, RETURN, LOAD_PART, RETURN), RESET_VECTOR=0x8000)

        found = walk._entries(rom, 0x8004, 1)

        self.assertEqual(found, (0x8004,))

    def test_every_published_vector_sits_in_the_header(self) -> None:
        outside = [one for one in walk.VECTORS if not 0x7FE4 <= one <= 0x7FFE]

        self.assertEqual(outside, [])


if __name__ == "__main__":
    unittest.main()
