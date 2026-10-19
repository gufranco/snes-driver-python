import sys
import unittest
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import corroborate

AT = 0x0100

WIDE = 0x00

NARROW = 0x20

NARROW_INDEX = 0x10

STORE_LONG = (0x8F, 0x00, 0x80, 0x3F)

STORE_X_ABSOLUTE = (0x8E, 0x00, 0x80)

STORE_INDEXED = (0x9D, 0x00, 0x80)

STORE_DIRECT = (0x85, 0x10)

LOAD_LONG = (0xAF, 0x00, 0x80, 0x3F)

INCREMENT_ABSOLUTE = (0xEE, 0x00, 0x80)

STORE_INDIRECT = (0x92, 0x10)


def an_image(code: Iterable[int], at: int = AT) -> bytes:
    rom = bytearray(0x8000)
    held = bytes(code)
    rom[at : at + len(held)] = held
    return bytes(rom)


def an_access(
    pc: int,
    address: int = 0x3F8000,
    width: int = 2,
    direction: str = "write",
    status: int = WIDE,
    emulation: bool = False,
    data_bank: int = 0x00,
    direct: int = 0x0000,
    x: int = 0x0000,
) -> corroborate.Access:
    return corroborate.Access(
        [
            direction,
            f"{address:06X}",
            str(width),
            f"{pc:06X}",
            f"{status:02X}",
            "1" if emulation else "0",
            f"{data_bank:02X}",
            f"{direct:04X}",
            f"{x:04X}",
            "0000",
            "3",
            "7",
        ]
    )


class AgreementTest(unittest.TestCase):
    def test_a_word_store_made_with_a_wide_accumulator_agrees(self) -> None:
        # Arrange
        rom = an_image(STORE_LONG)

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008104))

        # Assert
        self.assertEqual(
            (verdict.agrees, verdict.decoded.offset if verdict.decoded else None), (True, AT)
        )

    def test_the_instruction_it_found_is_named_with_its_start(self) -> None:
        # Arrange
        rom = an_image(STORE_LONG)

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008104))

        # Assert
        found = verdict.decoded
        self.assertEqual(
            (found.mnemonic, found.mode, found.start, found.expected) if found else None,
            ("sta", "absoluteLong", 0x008100, 2),
        )

    def test_a_read_is_counted_and_dated_as_the_trace_recorded_it(self) -> None:
        # Arrange
        line = an_access(0x008104, direction="read")

        # Act
        verdict = corroborate.corroborated(an_image(LOAD_LONG), "lorom", line)

        # Assert
        self.assertEqual((verdict.agrees, line.count, line.first), (True, 3, 7))

    def test_a_store_of_the_index_is_sized_by_the_index_flag(self) -> None:
        # Arrange
        rom = an_image(STORE_X_ABSOLUTE)

        # Act
        verdict = corroborate.corroborated(
            rom, "lorom", an_access(0x008103, address=0x008000, width=1, status=NARROW_INDEX)
        )

        # Assert
        self.assertTrue(verdict.agrees)

    def test_an_indexed_store_lands_at_the_bank_and_index_the_trace_held(self) -> None:
        # Arrange
        rom = an_image(STORE_INDEXED)

        # Act
        verdict = corroborate.corroborated(
            rom, "lorom", an_access(0x008103, address=0x3F8004, data_bank=0x3F, x=0x0004)
        )

        # Assert
        self.assertTrue(verdict.agrees)

    def test_a_narrow_index_drops_the_high_byte_it_still_holds(self) -> None:
        # Arrange
        rom = an_image(STORE_INDEXED)

        # Act
        verdict = corroborate.corroborated(
            rom,
            "lorom",
            an_access(0x008103, address=0x3F8004, data_bank=0x3F, x=0x1204, status=NARROW_INDEX),
        )

        # Assert
        self.assertTrue(verdict.agrees)

    def test_a_direct_page_store_lands_past_the_direct_register(self) -> None:
        # Arrange
        rom = an_image(STORE_DIRECT)

        # Act
        verdict = corroborate.corroborated(
            rom, "lorom", an_access(0x008102, address=0x006010, direct=0x6000)
        )

        # Assert
        self.assertTrue(verdict.agrees)

    def test_emulation_mode_moves_one_byte_whatever_the_status_holds(self) -> None:
        # Arrange
        rom = an_image(STORE_LONG)

        # Act
        verdict = corroborate.corroborated(
            rom, "lorom", an_access(0x008104, width=1, emulation=True)
        )

        # Assert
        self.assertTrue(verdict.agrees)

    def test_a_read_modify_write_fits_its_write_as_well_as_its_read(self) -> None:
        # Arrange
        rom = an_image(INCREMENT_ABSOLUTE)

        # Act
        verdict = corroborate.corroborated(
            rom, "lorom", an_access(0x008103, address=0x008000, width=1, status=NARROW)
        )

        # Assert
        self.assertTrue(verdict.agrees)

    def test_an_access_whose_address_no_operand_spells_is_taken_as_unchecked(self) -> None:
        # Arrange
        rom = an_image(STORE_INDIRECT)

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008102))

        # Assert
        found = verdict.decoded
        self.assertEqual((verdict.agrees, found.checked if found else None), (True, False))


class HalfTest(unittest.TestCase):
    def test_a_word_store_whose_low_byte_fell_outside_the_window_is_two_bytes(self) -> None:
        # Arrange
        rom = an_image((0x8D, 0xFF, 0x5F))

        # Act
        verdict = corroborate.corroborated(
            rom, "lorom", an_access(0x008103, address=0x006000, width=1)
        )

        # Assert
        self.assertEqual((verdict.agrees, verdict.width, verdict.half), (True, 2, "high"))

    def test_a_byte_store_one_below_the_address_explains_nothing(self) -> None:
        # Arrange
        rom = an_image((0x8D, 0xFF, 0x5F))

        # Act
        verdict = corroborate.corroborated(
            rom, "lorom", an_access(0x008103, address=0x006000, width=1, status=NARROW)
        )

        # Assert
        self.assertFalse(verdict.agrees)

    def test_a_whole_access_is_named_for_the_bytes_it_moved(self) -> None:
        # Arrange
        rom = an_image(STORE_LONG)

        # Act
        found = [
            corroborate.corroborated(rom, "lorom", an_access(0x008104, width=width, status=flag))
            for width, flag in ((2, WIDE), (1, NARROW))
        ]

        # Assert
        self.assertEqual([(one.width, one.half) for one in found], [(2, "both"), (1, "one")])


class DisagreementTest(unittest.TestCase):
    def test_an_immediate_operand_reaches_no_address(self) -> None:
        # Arrange
        rom = an_image((0xA9, 0x00, 0x80))

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008103, direction="read"))

        # Assert
        self.assertFalse(verdict.agrees)

    def test_a_width_the_flags_contradict_is_reported_with_both(self) -> None:
        # Arrange
        rom = an_image(STORE_LONG)

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008104, status=NARROW))

        # Assert
        self.assertEqual(
            verdict.reason, "the bus moved 2 bytes and sta under the recorded flags moves 1"
        )

    def test_an_access_no_instruction_explains_is_reported(self) -> None:
        # Arrange
        rom = an_image(())

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008104))

        # Assert
        self.assertEqual(
            (verdict.agrees, verdict.reason),
            (False, "no instruction ending at the recorded PC reaches the address"),
        )

    def test_an_instruction_begins_no_earlier_than_the_image_does(self) -> None:
        # Arrange
        rom = an_image(STORE_DIRECT, at=0)

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008002, address=0x000010))

        # Assert
        self.assertEqual(
            (verdict.agrees, verdict.decoded.start if verdict.decoded else None), (True, 0x008000)
        )

    def test_a_load_does_not_explain_a_write(self) -> None:
        # Arrange
        rom = an_image(LOAD_LONG)

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008104))

        # Assert
        self.assertFalse(verdict.agrees)

    def test_an_operand_spelling_another_address_does_not_explain_it(self) -> None:
        # Arrange
        rom = an_image(STORE_LONG)

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008104, address=0x3F8002))

        # Assert
        self.assertFalse(verdict.agrees)

    def test_a_pc_outside_the_image_explains_nothing(self) -> None:
        # Arrange
        rom = an_image(STORE_LONG)

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x7E0104))

        # Assert
        self.assertEqual(verdict.reason, "the instruction ran outside the image")

    def test_two_instructions_that_both_spell_the_address_are_ambiguous(self) -> None:
        # Arrange
        rom = an_image((0x8F, 0x00, 0x85, 0x00))

        # Act
        verdict = corroborate.corroborated(
            rom, "lorom", an_access(0x008104, address=0x008500, direct=0x8500)
        )

        # Assert
        self.assertEqual(verdict.reason, "more than one instruction ending at the recorded PC fits")

    def test_an_instruction_that_spells_the_address_wins_over_one_that_cannot(self) -> None:
        # Arrange
        rom = an_image((0x8F, 0x00, 0x92, 0x10))

        # Act
        verdict = corroborate.corroborated(rom, "lorom", an_access(0x008104, address=0x109200))

        # Assert
        found = verdict.decoded
        self.assertEqual((found.mnemonic, found.checked) if found else None, ("sta", True))


if __name__ == "__main__":
    unittest.main()
