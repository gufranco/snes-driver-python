import sys
import unittest
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver

NARROW = (0xE2, 0x20)
WIDE = (0xC2, 0x20)
POLL = (0xAD, 0x04, 0x38)
GUARD = (0x29, 0x10)
SKIP_THE_RETURN = (0xF0, 0x01)
SKIP_NOTHING = (0xF0, 0x00)
RETURN = (0x60,)
SEND = (0x8D, 0x02, 0x38)
RECEIVE = (0xAD, 0x00, 0x38)
LOOP_ON_THE_POLL = (0x10, 0xFB)
END_OF_BANK = 0x7FF0

WINDOW = snesdriver.WINDOWS["st018"]["lorom"]


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


def at_the_start(rom: bytes, window: object) -> tuple[int, ...]:
    return (0,)


GUARDED_SEND = assembled(NARROW, POLL, GUARD, SKIP_THE_RETURN, RETURN, SEND, RECEIVE, RETURN)


class ArmsTest(unittest.TestCase):
    def test_a_send_on_the_branch_target_and_its_receive_land_in_one_shape(self) -> None:
        # Arrange
        rom = GUARDED_SEND

        # Act
        found = snesdriver.shapes(rom, WINDOW, find=at_the_start)

        # Assert
        self.assertIn("poll1 write1 read1", found)

    def test_the_arm_that_falls_through_is_kept_beside_it(self) -> None:
        # Arrange
        rom = GUARDED_SEND

        # Act
        found = snesdriver.shapes(rom, WINDOW, find=at_the_start)

        # Assert
        self.assertEqual(found, {"poll1": 1, "poll1 write1 read1": 1})

    def test_each_arm_carries_the_width_the_code_set_before_the_branch(self) -> None:
        # Arrange
        rom = assembled(WIDE, POLL, GUARD[:1], (0x10, 0x00), SKIP_THE_RETURN, RETURN, SEND, RETURN)

        # Act
        found = snesdriver.shapes(rom, WINDOW, find=at_the_start)

        # Assert
        self.assertEqual(found, {"poll2": 1, "poll2 write2": 1})

    def test_a_branch_backwards_is_a_loop_and_is_not_forked(self) -> None:
        # Arrange
        rom = assembled(NARROW, POLL, LOOP_ON_THE_POLL, RECEIVE, RETURN)

        # Act
        found = snesdriver.shapes(rom, WINDOW, find=at_the_start)

        # Assert
        self.assertEqual(found, {"poll1 read1": 1})

    def test_a_walk_with_no_forks_left_keeps_only_the_arm_it_falls_through(self) -> None:
        # Arrange
        rom = GUARDED_SEND

        # Act
        found = snesdriver.shapes(rom, WINDOW, find=at_the_start, forks=0)

        # Assert
        self.assertEqual(found, {"poll1": 1})

    def test_a_branch_left_unfollowed_is_counted_rather_than_dropped(self) -> None:
        # Arrange
        rom = GUARDED_SEND

        # Act
        found = snesdriver.conversation.heard(rom, WINDOW, find=at_the_start, forks=0)

        # Assert
        self.assertEqual((found.overflow, found.walks), (1, 1))

    def test_two_arms_that_meet_with_the_same_past_are_walked_once(self) -> None:
        # Arrange
        rom = assembled(NARROW, SKIP_NOTHING, SKIP_NOTHING, SEND, RETURN)

        # Act
        found = snesdriver.walk.arms(rom, 0)

        # Assert
        self.assertEqual((found.forks, found.merged, len(found.paths)), (2, 1, 3))

    def test_a_branch_whose_target_leaves_the_image_is_not_forked(self) -> None:
        # Arrange
        rom = bytes(END_OF_BANK) + assembled(NARROW, SEND, (0xF0, 0x7F), RETURN)

        # Act
        found = snesdriver.walk.arms(rom, END_OF_BANK)

        # Assert
        self.assertEqual((found.forks, len(found.paths)), (0, 1))

    def test_the_default_cap_sits_above_every_walk_measured(self) -> None:
        # Arrange
        measured_maximum = 18_691

        # Act
        cap = snesdriver.walk.DEFAULT_FORKS

        # Assert
        self.assertGreater(cap, measured_maximum)

    def test_the_walk_a_single_arm_reader_sees_is_the_first_arm(self) -> None:
        # Arrange
        rom = GUARDED_SEND

        # Act
        found = snesdriver.at(rom, 0, WINDOW)

        # Assert
        self.assertEqual(found.shape, "poll1")


if __name__ == "__main__":
    unittest.main()
