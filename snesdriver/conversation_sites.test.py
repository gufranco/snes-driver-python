import sys
import unittest
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


NARROW = (0xE2, 0x20)
STORE_DATA = (0x8F, 0x00, 0x80, 0x3F)
LOAD_DATA = (0xAF, 0x00, 0x80, 0x3F)
RETURN = (0x60,)
STORE_ABSOLUTE = (0x8D, 0x00, 0x38)
LOAD_STATUS_ABSOLUTE = (0xAD, 0x04, 0x38)

WINDOW = snesdriver.WINDOWS["dsp"]["lorom"]

ABSOLUTE_WINDOW = snesdriver.WINDOWS["st018"]["lorom"]


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
        self.assertEqual(found, {"write? read?": 1})

    def test_the_same_shape_twice_is_counted_rather_than_repeated(self) -> None:
        # Arrange
        one = assembled(NARROW, STORE_DATA, RETURN)
        rom = bytes(0x40) + one + bytes(0x40) + one + bytes(0x40)

        # Act
        found = snesdriver.shapes(rom, WINDOW)

        # Assert
        self.assertEqual(found, {"write?": 2})

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
            [("write", None, 0x68, 0x0020, True, 0x680020)],
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
        self.assertEqual(found, {"poll?": 1})

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
        self.assertEqual(found.shape, "poll? write?")

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
        self.assertEqual(found, {"write?": 1, "poll?": 1})


if __name__ == "__main__":
    unittest.main()
