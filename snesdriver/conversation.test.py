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
LOAD_STATUS_ABSOLUTE = (0xAD, 0x04, 0x38)

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


class SiteTest(unittest.TestCase):
    def test_an_instruction_reaching_the_window_is_a_site(self) -> None:
        # Arrange
        rom = bytes(0x400) + assembled(STORE_DATA, RETURN) + bytes(0x400)

        # Act
        found = snesdriver.sites(rom, WINDOW)

        # Assert
        self.assertEqual(found, (0x400,))

    def test_an_instruction_reaching_elsewhere_is_not(self) -> None:
        # Arrange
        rom = bytes(0x400) + assembled((0x8F, 0x00, 0x80, 0x10), RETURN)

        # Act
        found = snesdriver.sites(rom, WINDOW)

        # Assert
        self.assertEqual(found, ())

    def test_sites_come_back_once_each_in_the_order_they_sit_in_the_image(self) -> None:
        # Arrange
        rom = bytes(0x100) + assembled(STORE_DATA) + bytes(0x100) + assembled(LOAD_DATA)

        # Act
        found = snesdriver.sites(rom, WINDOW)

        # Assert
        self.assertEqual(found, (0x100, 0x204))

    def test_a_reference_split_across_the_end_of_the_image_is_not_a_site(self) -> None:
        # Arrange
        rom = bytes([0x8F, 0x00, 0x80])

        # Act
        found = snesdriver.sites(rom, WINDOW)

        # Assert
        self.assertEqual(found, ())


class SurveyTest(unittest.TestCase):
    def test_a_site_whose_walk_reads_nothing_yields_no_shape(self) -> None:
        # Arrange
        rom = bytes(0x40) + assembled(STORE_DATA, RETURN)

        # Act
        found = snesdriver.shapes(rom, WINDOW, limit=0)

        # Assert
        self.assertEqual(found, {})

    def test_a_rom_with_no_driver_yields_no_shapes(self) -> None:
        # Arrange
        rom = bytes(0x1000)

        # Act
        found = snesdriver.shapes(rom, WINDOW)

        # Assert
        self.assertEqual(found, {})

    def test_a_site_an_earlier_walk_stepped_over_starts_nothing(self) -> None:
        # Arrange
        rom = bytes(0x40) + assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN) + bytes(0x40)

        # Act
        found = snesdriver.shapes(rom, WINDOW)

        # Assert
        self.assertEqual(found, {"write1 read1": 1})

    def test_the_same_shape_twice_is_counted_rather_than_repeated(self) -> None:
        # Arrange
        one = assembled(NARROW, STORE_DATA, RETURN)
        rom = bytes(0x40) + one + bytes(0x40) + one + bytes(0x40)

        # Act
        found = snesdriver.shapes(rom, WINDOW)

        # Assert
        self.assertEqual(found, {"write1": 2})

    def test_a_survey_walks_at_the_width_it_is_given(self) -> None:
        # Arrange
        rom = bytes(0x40) + assembled(STORE_DATA, RETURN)

        # Act
        found = snesdriver.shapes(rom, WINDOW, narrow=False)

        # Assert
        self.assertEqual(found, {"write2": 1})


class BankTest(unittest.TestCase):
    def test_a_walked_conversation_carries_the_whole_address_on_every_step(self) -> None:
        # Arrange
        rom = bytearray(b"\xea" * 0x200)
        rom[0:4] = bytes((0x8F, 0x20, 0x00, 0x68))
        rom[4] = 0x60

        # Act
        found = snesdriver.at(bytes(rom), 0, snesdriver.WINDOWS["st"]["lorom-shared"])

        # Assert
        self.assertEqual(
            [
                (one.what, one.width, one.bank, one.address, one.banked, one.whole)
                for one in found.steps
            ],
            [("write", 1, 0x68, 0x0020, True, 0x680020)],
        )

    def test_a_walk_takes_anything_else_that_answers_the_same_question(self) -> None:
        # Arrange
        class Both:
            def __init__(self, covered: list[snesdriver.Window]) -> None:
                self.covered = covered

            def reaches(self, bank: int, address: int) -> str | None:
                for one in self.covered:
                    found = one.reaches(bank, address)
                    if found is not None:
                        return found
                return None

        both = Both([snesdriver.WINDOWS["st"]["lorom"], snesdriver.WINDOWS["st"]["lorom-shared"]])
        rom = bytearray(b"\xea" * 0x200)
        rom[0:4] = bytes((0x8F, 0x00, 0x00, 0x60))
        rom[4:8] = bytes((0x8F, 0x20, 0x00, 0x68))
        rom[8:12] = bytes((0x8F, 0x00, 0x00, 0x7E))
        rom[12] = 0x60

        # Act
        found = snesdriver.at(bytes(rom), 0, both)

        # Assert
        self.assertEqual([one.whole for one in found.steps], [0x600000, 0x680020])


def image(body: bytes, vector: int = 0x8000) -> bytes:
    rom = bytearray(0x8000)
    rom[: len(body)] = body
    rom[0x7FFC:0x7FFE] = vector.to_bytes(2, "little")
    return bytes(rom)


BEHIND_A_BRANCH = image(assembled((0xF0, 0x02), RETURN, (0xEA,), LOAD_STATUS_ABSOLUTE, RETURN))


class ReachedTest(unittest.TestCase):
    def test_a_sweep_finds_an_absolute_access_a_search_for_bytes_cannot(self) -> None:
        # Arrange
        rom = BEHIND_A_BRANCH

        # Act
        found = (snesdriver.reached(rom, ABSOLUTE_WINDOW), snesdriver.sites(rom, ABSOLUTE_WINDOW))

        # Assert
        self.assertEqual(found, ((0x0004,), ()))

    def test_a_sweep_finds_nothing_when_nothing_reaches_the_part(self) -> None:
        # Arrange
        rom = image(assembled((0x8D, 0x00, 0x21), RETURN))

        # Act
        found = snesdriver.reached(rom, ABSOLUTE_WINDOW)

        # Assert
        self.assertEqual(found, ())

    def test_a_survey_can_be_given_another_way_of_finding_sites(self) -> None:
        # Arrange
        rom = BEHIND_A_BRANCH

        # Act
        found = snesdriver.shapes(rom, ABSOLUTE_WINDOW, find=snesdriver.reached)

        # Assert
        self.assertEqual(found, {"poll1": 1})

    def test_a_survey_that_searches_for_bytes_finds_nothing_there(self) -> None:
        # Arrange
        rom = BEHIND_A_BRANCH

        # Act
        found = snesdriver.shapes(rom, ABSOLUTE_WINDOW)

        # Assert
        self.assertEqual(found, {})


def calling(helper: bytes, after: bytes) -> bytes:
    body = bytearray((0x20, 0x00, 0x00))
    body += after
    at = 0x8000 + len(body)
    body[1], body[2] = at & 0xFF, at >> 8
    return bytes(body) + helper


THROUGH_A_HELPER = calling(
    assembled(LOAD_STATUS_ABSOLUTE, RETURN), assembled(STORE_ABSOLUTE, RETURN)
)


class ThroughAHelperTest(unittest.TestCase):
    def test_an_exchange_carries_what_the_helper_reached(self) -> None:
        # Arrange
        rom = THROUGH_A_HELPER

        # Act
        found = snesdriver.at(rom, 0, ABSOLUTE_WINDOW)

        # Assert
        self.assertEqual(found.shape, "poll1 write1")

    def test_only_the_calling_routine_counts_as_covered(self) -> None:
        # Arrange
        rom = THROUGH_A_HELPER

        # Act
        found = snesdriver.at(rom, 0, ABSOLUTE_WINDOW)

        # Assert
        self.assertEqual(sorted(found.covered), [0x0000, 0x0003, 0x0006])

    def test_a_site_inside_the_helper_still_starts_its_own_exchange(self) -> None:
        # Arrange
        rom = image(THROUGH_A_HELPER)

        # Act
        found = snesdriver.shapes(rom, ABSOLUTE_WINDOW, find=snesdriver.reached)

        # Assert
        self.assertEqual(found, {"write1": 1, "poll1": 1})


if __name__ == "__main__":
    unittest.main()
