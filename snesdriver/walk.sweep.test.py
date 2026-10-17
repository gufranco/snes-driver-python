import sys
import unittest
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


RETURN = (0x60,)
NOTHING = (0xEA,)
STORE_PART = (0x8D, 0x00, 0x38)
LOAD_PART = (0xAD, 0x04, 0x38)
STORE_LONG_PART = (0x8F, 0x02, 0x38, 0x00)
BANK = 0x8000
RESET = 0x7FFC

WINDOW = snesdriver.WINDOWS["st018"]["lorom"]


def image(body: bytes, vector: int = 0x8000, banks: int = 1) -> bytes:
    rom = bytearray(BANK * banks)
    rom[: len(body)] = body
    rom[RESET : RESET + 2] = vector.to_bytes(2, "little")
    return bytes(rom)


def reached(rom: bytes, entry: int | None = None, kind: str = "lorom") -> tuple[int, ...]:
    return snesdriver.reached(rom, WINDOW, entry, kind)


BRANCHING = assembled(
    STORE_PART,
    (0x20, 0x10, 0x80),
    (0xF0, 0x02),
    RETURN,
    NOTHING,
    LOAD_PART,
    (0x4C, 0x14, 0x80),
    STORE_LONG_PART,
    RETURN,
)


class SweepTest(unittest.TestCase):
    def test_a_sweep_reads_every_path_from_the_reset_vector(self) -> None:
        # Arrange
        rom = image(BRANCHING)

        # Act
        found = reached(rom)

        # Assert
        self.assertEqual(found, (0x0000, 0x000A, 0x0010))

    def test_a_sweep_starts_where_it_is_told_instead(self) -> None:
        # Arrange
        rom = image(BRANCHING)

        # Act
        found = reached(rom, 0x8010)

        # Assert
        self.assertEqual(found, (0x0010,))

    def test_a_sweep_takes_the_side_a_branch_jumps_to(self) -> None:
        # Arrange
        rom = image(assembled((0xF0, 0x03), RETURN, NOTHING, NOTHING, STORE_PART, RETURN))

        # Act
        found = reached(rom)

        # Assert
        self.assertEqual(found, (0x0005,))

    def test_a_sweep_takes_the_side_a_branch_falls_through_to(self) -> None:
        # Arrange
        rom = image(assembled((0xF0, 0x04), STORE_PART, RETURN, RETURN))

        # Act
        found = reached(rom)

        # Assert
        self.assertEqual(found, (0x0002,))

    def test_a_backward_branch_lands_before_itself(self) -> None:
        # Arrange
        body = bytearray(0x13)
        body[0:7] = assembled((0x4C, 0x10, 0x80), STORE_PART, RETURN)
        body[0x10:0x13] = assembled((0xF0, 0xF1), RETURN)

        # Act
        found = reached(image(bytes(body)))

        # Assert
        self.assertEqual(found, (0x0003,))

    def test_a_long_branch_lands_two_bytes_of_displacement_away(self) -> None:
        # Arrange
        body = bytearray(0x107)
        body[0:3] = (0x82, 0x00, 0x01)
        body[0x103:0x107] = assembled(STORE_PART, RETURN)

        # Act
        found = reached(image(bytes(body)))

        # Assert
        self.assertEqual(found, (0x0103,))

    def test_a_long_branch_backwards_lands_before_itself(self) -> None:
        # Arrange
        body = bytearray(0x13)
        body[0:7] = assembled((0x4C, 0x10, 0x80), STORE_PART, RETURN)
        body[0x10:0x13] = (0x82, 0xF0, 0xFF)

        # Act
        found = reached(image(bytes(body)))

        # Assert
        self.assertEqual(found, (0x0003,))

    def test_a_sweep_follows_a_call(self) -> None:
        # Arrange
        body = bytearray(0x14)
        body[0:4] = assembled((0x20, 0x10, 0x80), RETURN)
        body[0x10:0x14] = assembled(STORE_PART, RETURN)

        # Act
        found = reached(image(bytes(body)))

        # Assert
        self.assertEqual(found, (0x0010,))

    def test_a_call_lands_in_the_bank_it_was_made_from(self) -> None:
        # Arrange
        rom = bytearray(image(assembled((0x5C, 0x00, 0x80, 0x01)), banks=2))
        rom[0x0010:0x0014] = assembled(STORE_PART, RETURN)
        rom[0x8000:0x8004] = assembled((0x20, 0x10, 0x80), RETURN)
        rom[0x8010:0x8014] = assembled(LOAD_PART, RETURN)

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, (0x8010,))

    def test_an_absolute_access_reaches_the_bank_the_sweep_is_walking(self) -> None:
        # Arrange
        rom = bytearray(image(assembled((0x5C, 0x00, 0x80, 0x01)), banks=2))
        rom[0x8000:0x8004] = assembled(STORE_PART, RETURN)
        second_bank_only = snesdriver.Window(0x01, 0x01, 0x3800, 0x3804, 0x3803)

        # Act
        found = snesdriver.reached(bytes(rom), second_bank_only)

        # Assert
        self.assertEqual(found, (0x8000,))

    def test_a_long_call_carries_the_bank_it_goes_to(self) -> None:
        # Arrange
        rom = bytearray(image(assembled((0x22, 0x00, 0x90, 0x02), RETURN), banks=3))
        rom[0x11000:0x11004] = assembled(LOAD_PART, RETURN)

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, (0x11000,))

    def test_an_indirect_jump_is_not_followed_because_its_target_cannot_be_read(self) -> None:
        # Arrange
        body = bytearray(0x14)
        body[0:3] = (0x6C, 0x10, 0x80)
        body[0x10:0x14] = assembled(STORE_PART, RETURN)

        # Act
        found = reached(image(bytes(body)))

        # Assert
        self.assertEqual(found, ())

    def test_a_sweep_decodes_nothing_control_flow_never_arrives_at(self) -> None:
        # Arrange
        rom = image(assembled(RETURN, STORE_PART, RETURN))

        # Act
        found = reached(rom)

        # Assert
        self.assertEqual(found, ())

    def test_a_sweep_reads_nothing_below_the_cartridge(self) -> None:
        # Arrange
        rom = image(BRANCHING)

        # Act
        found = reached(rom, 0x0000)

        # Assert
        self.assertEqual(found, ())

    def test_a_sweep_does_not_follow_a_jump_out_of_the_image(self) -> None:
        # Arrange
        rom = image(assembled((0x5C, 0x00, 0x80, 0x7E), STORE_PART, RETURN))

        # Act
        found = reached(rom)

        # Assert
        self.assertEqual(found, ())


class WidthAcrossBranchesTest(unittest.TestCase):
    def test_a_sweep_starts_with_the_accumulator_reset_leaves_at_eight_bits(self) -> None:
        # Arrange
        rom = image(assembled((0xA9, 0x34), STORE_PART, RETURN))

        # Act
        found = reached(rom)

        # Assert
        self.assertEqual(found, (0x0002,))

    def test_a_sweep_carries_a_widened_accumulator_across_a_branch(self) -> None:
        # Arrange
        body = assembled((0xC2, 0x20), (0xF0, 0x01), RETURN, (0xA9, 0x34, 0x12), STORE_PART)

        # Act
        found = reached(image(body + bytes(RETURN)))

        # Assert
        self.assertEqual(found, (0x0008,))

    def test_and_narrowing_it_again_is_carried_too(self) -> None:
        # Arrange
        body = assembled((0xC2, 0x20), (0xE2, 0x20), (0xF0, 0x01), RETURN, (0xA9, 0x34))

        # Act
        found = reached(image(body + bytes(STORE_PART) + bytes(RETURN)))

        # Assert
        self.assertEqual(found, (0x0009,))

    def test_a_sweep_carries_a_widened_index_across_a_branch(self) -> None:
        # Arrange
        body = assembled((0xC2, 0x10), (0xF0, 0x01), RETURN, (0xA0, 0x34, 0x12), STORE_PART)

        # Act
        found = reached(image(body + bytes(RETURN)))

        # Assert
        self.assertEqual(found, (0x0008,))

    def test_and_narrowing_the_index_again_is_carried_too(self) -> None:
        # Arrange
        body = assembled((0xC2, 0x10), (0xE2, 0x10), (0xF0, 0x01), RETURN, (0xA0, 0x34))

        # Act
        found = reached(image(body + bytes(STORE_PART) + bytes(RETURN)))

        # Assert
        self.assertEqual(found, (0x0009,))


PRINTED_VECTORS = (0xFFE4, 0xFFE6, 0xFFE8, 0xFFEA, 0xFFEE, 0xFFF4, 0xFFF8, 0xFFFA, 0xFFFC, 0xFFFE)

UNUSED_VECTORS = (0xFFE0, 0xFFE2, 0xFFEC, 0xFFF0, 0xFFF2, 0xFFF6)


def vectored(slots: "Iterable[int]", file_offset: int) -> tuple[bytearray, list[int]]:
    rom = bytearray(BANK * 2)
    routines = []
    for index, slot in enumerate(slots):
        routine = 0x100 * (index + 1)
        rom[routine : routine + 4] = assembled(STORE_PART, RETURN)
        at = file_offset + (slot & 0xFF)
        rom[at : at + 2] = (0x8000 + routine).to_bytes(2, "little")
        routines.append(routine)
    return rom, routines


class EntryTest(unittest.TestCase):
    def test_a_sweep_starts_at_each_of_the_ten_vectors_the_processor_defines(self) -> None:
        # Arrange
        rom, routines = vectored(PRINTED_VECTORS, 0x7F00)

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, tuple(routines))

    def test_and_at_none_of_the_slots_it_leaves_unused(self) -> None:
        # Arrange
        rom, _ = vectored(UNUSED_VECTORS, 0x7F00)

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, ())

    def test_a_high_cartridge_keeps_its_vectors_at_the_top_of_its_first_bank(self) -> None:
        # Arrange
        rom = bytearray(BANK * 2)
        rom[0x8000:0x8004] = assembled(STORE_PART, RETURN)
        rom[0x9000:0x9004] = assembled(LOAD_PART, RETURN)
        rom[0xFFFC:0xFFFE] = (0x8000).to_bytes(2, "little")
        rom[0x7FFC:0x7FFE] = (0x9000).to_bytes(2, "little")

        # Act
        found = reached(bytes(rom), kind="hirom")

        # Assert
        self.assertEqual(found, (0x8000,))

    def test_an_image_too_short_to_hold_its_vectors_starts_nowhere(self) -> None:
        # Arrange
        rom = assembled(STORE_PART, RETURN)

        # Act
        found = reached(rom)

        # Assert
        self.assertEqual(found, ())

    def test_a_vector_pointing_below_the_cartridge_is_not_a_start(self) -> None:
        # Arrange
        rom = bytearray(image(assembled(STORE_PART, RETURN)))
        rom[0x7FEA:0x7FEC] = (0x0000).to_bytes(2, "little")

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, (0x0000,))

    def test_a_routine_two_entries_reach_is_read_from_the_first_that_arrives(self) -> None:
        # Arrange
        rom = bytearray(image(assembled((0x4C, 0x00, 0x80))))
        rom[0x0010:0x0014] = assembled(STORE_PART, RETURN)
        rom[0x7FEA:0x7FEC] = (0x8010).to_bytes(2, "little")

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, (0x0010,))


def a_high_cartridge() -> bytes:
    rom = bytearray(BANK * 2)
    rom[0x8000:0x8004] = (0x5C, 0x00, 0x00, 0xC0)
    rom[0x0000:0x0005] = assembled(STORE_LONG_PART, RETURN)
    rom[0xFFFC:0xFFFE] = (0x8000).to_bytes(2, "little")
    return bytes(rom)


class LayoutTest(unittest.TestCase):
    def test_a_sweep_told_a_high_map_follows_a_jump_into_the_high_banks(self) -> None:
        # Arrange
        rom = a_high_cartridge()

        # Act
        found = reached(rom, kind="hirom")

        # Assert
        self.assertEqual(found, (0x0000,))

    def test_the_same_image_read_as_a_low_one_never_reaches_it(self) -> None:
        # Arrange
        rom = a_high_cartridge()

        # Act
        found = reached(rom)

        # Assert
        self.assertEqual(found, ())

    def test_a_low_map_reads_a_mirrored_bank_as_the_bank_it_mirrors(self) -> None:
        # Arrange
        rom = bytearray(image(assembled((0x5C, 0x00, 0x80, 0x81)), banks=2))
        rom[0x8000:0x8005] = assembled(STORE_LONG_PART, RETURN)

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, (0x8000,))

    def test_a_bank_the_image_does_not_have_is_read_as_nothing(self) -> None:
        # Arrange
        rom = bytearray(image(assembled((0x5C, 0x10, 0x80, 0x02)), banks=2))
        rom[0x0010:0x0014] = assembled(STORE_PART, RETURN)

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, ())


class EdgeTest(unittest.TestCase):
    def test_a_sweep_stops_where_the_image_runs_out(self) -> None:
        # Arrange
        rom = bytearray(image(assembled((0x5C, 0xFF, 0xFF, 0x01)), banks=2))
        rom[0xFFFF] = 0xAF

        # Act
        found = reached(bytes(rom))

        # Assert
        self.assertEqual(found, ())

    def test_a_sweep_stops_at_the_top_of_a_bank_rather_than_run_into_the_next(self) -> None:
        # Arrange
        rom = bytearray(BANK * 4)
        rom[0x8000:0x8004] = (0x5C, 0xFF, 0xFF, 0xC0)
        rom[0xFFFF] = 0xEA
        rom[0x10000:0x10004] = STORE_LONG_PART

        # Act
        found = reached(bytes(rom), 0x8000, "hirom")

        # Assert
        self.assertEqual(found, ())

    def test_a_sweep_stops_after_four_hundred_thousand_instructions(self) -> None:
        # Arrange
        banks = 13
        rom = bytearray(bytes(NOTHING) * (BANK * banks))
        for bank in range(banks - 1):
            rom[bank * BANK + 0x7FFC : (bank + 1) * BANK] = (0x5C, 0x00, 0x80, bank + 1)
        last = (banks - 1) * BANK
        rom[last + 0x100 : last + 0x103] = STORE_PART
        rom[last + 0x2000 : last + 0x2003] = STORE_PART

        # Act
        found = reached(bytes(rom), 0x8000)

        # Assert
        self.assertEqual(found, (last + 0x100,))


if __name__ == "__main__":
    unittest.main()
