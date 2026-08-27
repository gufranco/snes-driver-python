import sys
import unittest
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesdriver import conversation, windows


def assembled(*chunks: "Iterable[int]") -> bytes:
    return bytes(b for chunk in chunks for b in chunk)


NARROW = (0xE2, 0x20)
WIDE = (0xC2, 0x20)
STORE_DATA = (0x8F, 0x00, 0x80, 0x3F)
LOAD_DATA = (0xAF, 0x00, 0x80, 0x3F)
LOAD_STATUS = (0xAF, 0x00, 0xC0, 0x3F)
RETURN = (0x60,)
STORE_ABSOLUTE = (0x8D, 0x00, 0x38)

WINDOW = windows.WINDOWS["dsp"]["lorom"]


class ShapeTest(unittest.TestCase):
    def test_a_write_to_the_data_register_is_a_write(self) -> None:
        found = conversation.at(assembled(STORE_DATA, RETURN), 0, WINDOW)

        self.assertEqual([step.what for step in found.steps], [conversation.WRITE])

    def test_a_read_of_the_data_register_is_a_read(self) -> None:
        found = conversation.at(assembled(LOAD_DATA, RETURN), 0, WINDOW)

        self.assertEqual([step.what for step in found.steps], [conversation.READ])

    def test_a_read_of_the_status_register_is_a_poll(self) -> None:
        found = conversation.at(assembled(LOAD_STATUS, RETURN), 0, WINDOW)

        self.assertEqual([step.what for step in found.steps], [conversation.POLL])

    def test_an_instruction_touching_nothing_is_not_a_step(self) -> None:
        found = conversation.at(assembled((0xA9, 0x06), RETURN), 0, WINDOW, narrow=True)

        self.assertEqual(found.steps, ())

    def test_the_width_of_a_step_follows_the_accumulator(self) -> None:
        narrow = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW, narrow=False)
        wide = conversation.at(assembled(WIDE, STORE_DATA, RETURN), 0, WINDOW, narrow=True)

        self.assertEqual(narrow.steps[0].width, 1)
        self.assertEqual(wide.steps[0].width, 2)

    def test_the_bytes_a_conversation_moves_are_counted_by_width(self) -> None:
        found = conversation.at(assembled(WIDE, STORE_DATA, STORE_DATA, RETURN), 0, WINDOW)

        self.assertEqual(found.written, 4)

    def test_and_the_bytes_it_takes_back(self) -> None:
        found = conversation.at(assembled(NARROW, LOAD_DATA, LOAD_DATA, RETURN), 0, WINDOW)

        self.assertEqual(found.read, 2)

    def test_a_poll_moves_nothing_either_way(self) -> None:
        found = conversation.at(assembled(NARROW, LOAD_STATUS, RETURN), 0, WINDOW)

        self.assertEqual((found.written, found.read), (0, 0))

    def test_whether_the_routine_waits_on_the_part_is_reported(self) -> None:
        polling = conversation.at(assembled(NARROW, LOAD_STATUS, RETURN), 0, WINDOW)
        silent = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW)

        self.assertTrue(polling.polls)
        self.assertFalse(silent.polls)


class StepTest(unittest.TestCase):
    def test_a_step_prints_as_what_it_is_and_how_wide(self) -> None:
        found = conversation.at(assembled(WIDE, STORE_DATA, RETURN), 0, WINDOW)

        self.assertIn(conversation.WRITE, repr(found.steps[0]))
        self.assertIn("2", repr(found.steps[0]))


class ShapeIdentityTest(unittest.TestCase):
    def test_two_routines_doing_the_same_thing_share_a_shape(self) -> None:
        one = conversation.at(assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN), 0, WINDOW)
        two = conversation.at(assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN), 0, WINDOW)

        self.assertEqual(one.shape, two.shape)

    def test_a_routine_writing_a_different_number_of_bytes_does_not(self) -> None:
        one = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW)
        two = conversation.at(assembled(NARROW, STORE_DATA, STORE_DATA, RETURN), 0, WINDOW)

        self.assertNotEqual(one.shape, two.shape)

    def test_a_shape_reads_as_the_exchange_it_describes(self) -> None:
        found = conversation.at(assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN), 0, WINDOW)

        self.assertIn("write", found.shape)
        self.assertIn("read", found.shape)

    def test_a_conversation_prints_as_its_shape(self) -> None:
        found = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW)

        self.assertIn(found.shape, repr(found))

    def test_a_conversation_of_long_accesses_carried_every_bank_it_reached(self) -> None:
        found = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW)

        self.assertTrue(found.banked)

    def test_and_one_reached_absolutely_did_not(self) -> None:
        """The bank of an absolute access is the routine's own, not the
        instruction's, so a caller recording the shape has to be told.
        """
        window = windows.WINDOWS["st018"]["lorom"]

        found = conversation.at(assembled(NARROW, STORE_ABSOLUTE, RETURN), 0, window)

        self.assertEqual((found.shape, found.banked), ("write1", False))

    def test_a_conversation_that_touches_nothing_says_so(self) -> None:
        found = conversation.at(assembled((0xA9, 0x06), RETURN), 0, WINDOW, narrow=True)

        self.assertFalse(found)

    def test_and_one_that_does_is_truthy(self) -> None:
        self.assertTrue(conversation.at(assembled(STORE_DATA, RETURN), 0, WINDOW))


class SiteTest(unittest.TestCase):
    def test_an_instruction_reaching_the_window_is_a_site(self) -> None:
        rom = bytes(0x400) + assembled(STORE_DATA, RETURN) + bytes(0x400)

        self.assertIn(0x400, conversation.sites(rom, WINDOW))

    def test_an_instruction_reaching_elsewhere_is_not(self) -> None:
        rom = bytes(0x400) + assembled((0x8F, 0x00, 0x80, 0x10), RETURN)

        self.assertEqual(conversation.sites(rom, WINDOW), ())

    def test_every_site_is_reported_once(self) -> None:
        rom = assembled(STORE_DATA, STORE_DATA, RETURN)

        self.assertEqual(
            len(conversation.sites(rom, WINDOW)), len(set(conversation.sites(rom, WINDOW)))
        )

    def test_sites_come_back_in_the_order_they_sit_in_the_image(self) -> None:
        rom = bytes(0x100) + assembled(STORE_DATA) + bytes(0x100) + assembled(LOAD_DATA)

        found = conversation.sites(rom, WINDOW)

        self.assertEqual(list(found), sorted(found))

    def test_a_reference_split_across_the_end_of_the_image_is_not_a_site(self) -> None:
        self.assertEqual(conversation.sites(bytes([0x8F, 0x00, 0x80]), WINDOW), ())


class SurveyTest(unittest.TestCase):
    def test_a_site_whose_walk_reads_nothing_yields_no_shape(self) -> None:
        rom = bytes(0x40) + assembled(STORE_DATA, RETURN)

        self.assertEqual(conversation.shapes(rom, WINDOW, limit=0), {})
        self.assertTrue(conversation.sites(rom, WINDOW))

    def test_a_rom_with_no_driver_yields_no_shapes(self) -> None:
        self.assertEqual(conversation.shapes(bytes(0x1000), WINDOW), {})

    def test_a_rom_with_one_routine_yields_its_shape(self) -> None:
        rom = bytes(0x100) + assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN) + bytes(0x100)

        found = conversation.shapes(rom, WINDOW)

        self.assertEqual(len(found), 1)

    def test_a_site_an_earlier_walk_stepped_over_starts_nothing(self) -> None:
        rom = bytes(0x40) + assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN) + bytes(0x40)

        found = conversation.shapes(rom, WINDOW)

        self.assertEqual(sum(found.values()), 1)
        self.assertEqual(len(conversation.sites(rom, WINDOW)), 2)

    def test_the_same_shape_twice_is_counted_rather_than_repeated(self) -> None:
        one = assembled(NARROW, STORE_DATA, RETURN)
        rom = bytes(0x40) + one + bytes(0x40) + one + bytes(0x40)

        found = conversation.shapes(rom, WINDOW)

        self.assertEqual(sum(found.values()), len(conversation.sites(rom, WINDOW)))


class BankTest(unittest.TestCase):
    def test_a_step_carries_the_bank_the_instruction_named(self) -> None:
        one = conversation.Step(conversation.READ, 1, 0x0020, 0x68)

        self.assertEqual(one.whole, 0x680020)

    def test_a_step_with_no_bank_has_no_whole_address(self) -> None:
        one = conversation.Step(conversation.READ, 1, 0x0020)

        self.assertIsNone(one.whole)

    def test_a_step_with_no_address_has_none_either(self) -> None:
        one = conversation.Step(conversation.READ, 1, None, 0x68)

        self.assertIsNone(one.whole)

    def test_a_window_satisfies_the_one_question_a_walk_asks_it(self) -> None:
        self.assertIsInstance(windows.WINDOWS["dsp"]["lorom"], conversation.Reaching)

    def test_a_walk_takes_anything_else_that_answers_the_same_question(self) -> None:
        class Both:
            def __init__(self, covered: list[windows.Window]) -> None:
                self.covered = covered

            def reaches(self, bank: int, address: int) -> str | None:
                for one in self.covered:
                    found = one.reaches(bank, address)
                    if found is not None:
                        return found
                return None

        both = Both([windows.WINDOWS["st"]["lorom"], windows.WINDOWS["st"]["lorom-shared"]])
        rom = bytearray(b"\xea" * 0x200)
        rom[0:4] = bytes((0x8F, 0x00, 0x00, 0x60))
        rom[4:8] = bytes((0x8F, 0x20, 0x00, 0x68))
        rom[8:12] = bytes((0x8F, 0x00, 0x00, 0x7E))
        rom[12] = 0x60

        talk = conversation.at(bytes(rom), 0, both)

        self.assertEqual([one.whole for one in talk.steps], [0x600000, 0x680020])

    def test_a_walked_conversation_carries_the_bank_on_every_step(self) -> None:
        rom = bytearray(b"\xea" * 0x200)
        rom[0:4] = bytes((0x8F, 0x00, 0x00, 0x68))
        rom[4] = 0x60

        talk = conversation.at(bytes(rom), 0, windows.WINDOWS["st"]["lorom-shared"])

        self.assertEqual([one.whole for one in talk.steps], [0x680000])


if __name__ == "__main__":
    unittest.main()
