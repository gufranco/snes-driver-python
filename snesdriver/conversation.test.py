import sys
import unittest
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


NARROW = (0xE2, 0x20)
WIDE = (0xC2, 0x20)
STORE_DATA = (0x8F, 0x00, 0x80, 0x3F)
LOAD_DATA = (0xAF, 0x00, 0x80, 0x3F)
LOAD_STATUS = (0xAF, 0x00, 0xC0, 0x3F)
RETURN = (0x60,)
STORE_ABSOLUTE = (0x8D, 0x00, 0x38)

WINDOW = snesdriver.WINDOWS["dsp"]["lorom"]

ABSOLUTE_WINDOW = snesdriver.WINDOWS["st018"]["lorom"]


def talk(*chunks: "Iterable[int]", **options: Any) -> Any:
    return snesdriver.at(assembled(*chunks), 0, WINDOW, **options)


class ShapeTest(unittest.TestCase):
    def test_a_write_to_the_data_register_is_a_write(self) -> None:
        # Arrange
        code = (STORE_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual([step.what for step in found.steps], ["write"])

    def test_a_read_of_the_data_register_is_a_read(self) -> None:
        # Arrange
        code = (LOAD_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual([step.what for step in found.steps], ["read"])

    def test_a_read_of_the_status_register_is_a_poll(self) -> None:
        # Arrange
        code = (LOAD_STATUS, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual([step.what for step in found.steps], ["poll"])

    def test_the_three_kinds_are_published_by_the_names_the_readme_gives(self) -> None:
        # Arrange
        names = ("WRITE", "READ", "POLL")

        # Act
        found = [getattr(snesdriver, name) for name in names]

        # Assert
        self.assertEqual(found, ["write", "read", "poll"])

    def test_an_instruction_touching_nothing_is_not_a_step(self) -> None:
        # Arrange
        code = ((0xA9, 0x06), RETURN)

        # Act
        found = talk(*code, narrow=True)

        # Assert
        self.assertEqual(found.steps, ())

    def test_the_width_of_a_step_follows_the_accumulator(self) -> None:
        # Arrange
        narrowed = (NARROW, STORE_DATA, RETURN)

        # Act
        found = talk(*narrowed, narrow=False)

        # Assert
        self.assertEqual(found.steps[0].width, 1)

    def test_and_so_does_a_widened_one(self) -> None:
        # Arrange
        widened = (WIDE, STORE_DATA, RETURN)

        # Act
        found = talk(*widened, narrow=True)

        # Assert
        self.assertEqual(found.steps[0].width, 2)

    def test_the_bytes_a_conversation_moves_are_counted_by_width(self) -> None:
        # Arrange
        code = (WIDE, STORE_DATA, STORE_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual(found.written, 4)

    def test_and_the_bytes_it_takes_back(self) -> None:
        # Arrange
        code = (WIDE, LOAD_DATA, LOAD_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual(found.read, 4)

    def test_a_poll_moves_nothing_either_way(self) -> None:
        # Arrange
        code = (NARROW, STORE_DATA, LOAD_STATUS, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual((found.written, found.read, found.polls), (1, 0, True))

    def test_a_routine_that_never_polls_says_so(self) -> None:
        # Arrange
        code = (NARROW, STORE_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertFalse(found.polls)

    def test_a_step_prints_as_what_it_is_and_how_wide(self) -> None:
        # Arrange
        code = (WIDE, STORE_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual(repr(found.steps[0]), "<write 2>")

    def test_a_walk_can_be_held_to_fewer_instructions(self) -> None:
        # Arrange
        code = (NARROW, STORE_DATA, STORE_DATA, RETURN)

        # Act
        found = talk(*code, limit=2)

        # Assert
        self.assertEqual(found.shape, "write1")


class ShapeIdentityTest(unittest.TestCase):
    def test_the_same_routine_anywhere_in_the_image_has_the_same_shape(self) -> None:
        # Arrange
        rom = bytes(0x40) + assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN)

        # Act
        found = snesdriver.at(rom, 0x40, WINDOW)

        # Assert
        self.assertEqual(found.shape, "write1 read1")

    def test_a_routine_writing_a_different_number_of_bytes_has_another(self) -> None:
        # Arrange
        code = (NARROW, STORE_DATA, STORE_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual(found.shape, "write1 write1")

    def test_a_shape_reads_as_the_exchange_it_describes(self) -> None:
        # Arrange
        code = (NARROW, STORE_DATA, LOAD_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual(found.shape, "write1 read1")

    def test_a_conversation_prints_as_its_shape(self) -> None:
        # Arrange
        code = (NARROW, STORE_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual(repr(found), "<Conversation write1>")

    def test_and_one_that_reached_nothing_prints_as_nothing(self) -> None:
        # Arrange
        code = ((0xA9, 0x06), RETURN)

        # Act
        found = talk(*code, narrow=True)

        # Assert
        self.assertEqual(repr(found), "<Conversation nothing>")

    def test_a_conversation_of_long_accesses_carried_every_bank_it_reached(self) -> None:
        # Arrange
        code = (NARROW, STORE_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertTrue(found.banked)

    def test_and_one_reached_absolutely_did_not(self) -> None:
        # Arrange
        code = assembled(NARROW, (0x8F, 0x00, 0x38, 0x00), STORE_ABSOLUTE, RETURN)

        # Act
        found = snesdriver.at(code, 0, ABSOLUTE_WINDOW)

        # Assert
        self.assertEqual((found.shape, found.banked), ("write1 write1", False))

    def test_a_conversation_that_touches_nothing_is_false(self) -> None:
        # Arrange
        code = ((0xA9, 0x06), RETURN)

        # Act
        found = talk(*code, narrow=True)

        # Assert
        self.assertFalse(found)

    def test_and_one_that_does_is_true(self) -> None:
        # Arrange
        code = (STORE_DATA, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertTrue(found)


class ModuleContentsTest(unittest.TestCase):
    def test_each_entry_in_steps_is_the_class_the_readme_names(self) -> None:
        # Arrange
        code = (NARROW, STORE_DATA, LOAD_STATUS, RETURN)

        # Act
        found = talk(*code)

        # Assert
        self.assertEqual({type(step) for step in found.steps}, {snesdriver.conversation.Step})


if __name__ == "__main__":
    unittest.main()
