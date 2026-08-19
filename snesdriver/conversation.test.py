import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesdriver import conversation, windows


def assembled(*chunks):
    return bytes(b for chunk in chunks for b in chunk)


NARROW = (0xE2, 0x20)
WIDE = (0xC2, 0x20)
STORE_DATA = (0x8F, 0x00, 0x80, 0x3F)
LOAD_DATA = (0xAF, 0x00, 0x80, 0x3F)
LOAD_STATUS = (0xAF, 0x00, 0xC0, 0x3F)
RETURN = (0x60,)

WINDOW = windows.WINDOWS["dsp"]["lorom"]


class ShapeTest(unittest.TestCase):
    def test_a_write_to_the_data_register_is_a_write(self):
        found = conversation.at(assembled(STORE_DATA, RETURN), 0, WINDOW)

        self.assertEqual([step.what for step in found.steps], [conversation.WRITE])

    def test_a_read_of_the_data_register_is_a_read(self):
        found = conversation.at(assembled(LOAD_DATA, RETURN), 0, WINDOW)

        self.assertEqual([step.what for step in found.steps], [conversation.READ])

    def test_a_read_of_the_status_register_is_a_poll(self):
        found = conversation.at(assembled(LOAD_STATUS, RETURN), 0, WINDOW)

        self.assertEqual([step.what for step in found.steps], [conversation.POLL])

    def test_an_instruction_touching_nothing_is_not_a_step(self):
        found = conversation.at(assembled((0xA9, 0x06), RETURN), 0, WINDOW, narrow=True)

        self.assertEqual(found.steps, ())

    def test_the_width_of_a_step_follows_the_accumulator(self):
        narrow = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW, narrow=False)
        wide = conversation.at(assembled(WIDE, STORE_DATA, RETURN), 0, WINDOW, narrow=True)

        self.assertEqual(narrow.steps[0].width, 1)
        self.assertEqual(wide.steps[0].width, 2)

    def test_the_bytes_a_conversation_moves_are_counted_by_width(self):
        found = conversation.at(assembled(WIDE, STORE_DATA, STORE_DATA, RETURN), 0, WINDOW)

        self.assertEqual(found.written, 4)

    def test_and_the_bytes_it_takes_back(self):
        found = conversation.at(assembled(NARROW, LOAD_DATA, LOAD_DATA, RETURN), 0, WINDOW)

        self.assertEqual(found.read, 2)

    def test_a_poll_moves_nothing_either_way(self):
        found = conversation.at(assembled(NARROW, LOAD_STATUS, RETURN), 0, WINDOW)

        self.assertEqual((found.written, found.read), (0, 0))

    def test_whether_the_routine_waits_on_the_part_is_reported(self):
        polling = conversation.at(assembled(NARROW, LOAD_STATUS, RETURN), 0, WINDOW)
        silent = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW)

        self.assertTrue(polling.polls)
        self.assertFalse(silent.polls)


class StepTest(unittest.TestCase):
    def test_a_step_prints_as_what_it_is_and_how_wide(self):
        found = conversation.at(assembled(WIDE, STORE_DATA, RETURN), 0, WINDOW)

        self.assertIn(conversation.WRITE, repr(found.steps[0]))
        self.assertIn("2", repr(found.steps[0]))


class ShapeIdentityTest(unittest.TestCase):
    def test_two_routines_doing_the_same_thing_share_a_shape(self):
        one = conversation.at(assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN), 0, WINDOW)
        two = conversation.at(assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN), 0, WINDOW)

        self.assertEqual(one.shape, two.shape)

    def test_a_routine_writing_a_different_number_of_bytes_does_not(self):
        one = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW)
        two = conversation.at(assembled(NARROW, STORE_DATA, STORE_DATA, RETURN), 0, WINDOW)

        self.assertNotEqual(one.shape, two.shape)

    def test_a_shape_reads_as_the_exchange_it_describes(self):
        found = conversation.at(assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN), 0, WINDOW)

        self.assertIn("write", found.shape)
        self.assertIn("read", found.shape)

    def test_a_conversation_prints_as_its_shape(self):
        found = conversation.at(assembled(NARROW, STORE_DATA, RETURN), 0, WINDOW)

        self.assertIn(found.shape, repr(found))

    def test_a_conversation_that_touches_nothing_says_so(self):
        found = conversation.at(assembled((0xA9, 0x06), RETURN), 0, WINDOW, narrow=True)

        self.assertFalse(found)

    def test_and_one_that_does_is_truthy(self):
        self.assertTrue(conversation.at(assembled(STORE_DATA, RETURN), 0, WINDOW))


class SiteTest(unittest.TestCase):
    def test_an_instruction_reaching_the_window_is_a_site(self):
        rom = bytes(0x400) + assembled(STORE_DATA, RETURN) + bytes(0x400)

        self.assertIn(0x400, conversation.sites(rom, WINDOW))

    def test_an_instruction_reaching_elsewhere_is_not(self):
        rom = bytes(0x400) + assembled((0x8F, 0x00, 0x80, 0x10), RETURN)

        self.assertEqual(conversation.sites(rom, WINDOW), ())

    def test_every_site_is_reported_once(self):
        rom = assembled(STORE_DATA, STORE_DATA, RETURN)

        self.assertEqual(
            len(conversation.sites(rom, WINDOW)), len(set(conversation.sites(rom, WINDOW)))
        )

    def test_sites_come_back_in_the_order_they_sit_in_the_image(self):
        rom = bytes(0x100) + assembled(STORE_DATA) + bytes(0x100) + assembled(LOAD_DATA)

        found = conversation.sites(rom, WINDOW)

        self.assertEqual(list(found), sorted(found))

    def test_a_reference_split_across_the_end_of_the_image_is_not_a_site(self):
        self.assertEqual(conversation.sites(bytes([0x8F, 0x00, 0x80]), WINDOW), ())


class SurveyTest(unittest.TestCase):
    def test_a_site_whose_walk_reads_nothing_yields_no_shape(self):
        rom = bytes(0x40) + assembled(STORE_DATA, RETURN)

        self.assertEqual(conversation.shapes(rom, WINDOW, limit=0), {})
        self.assertTrue(conversation.sites(rom, WINDOW))

    def test_a_rom_with_no_driver_yields_no_shapes(self):
        self.assertEqual(conversation.shapes(bytes(0x1000), WINDOW), {})

    def test_a_rom_with_one_routine_yields_its_shape(self):
        rom = bytes(0x100) + assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN) + bytes(0x100)

        found = conversation.shapes(rom, WINDOW)

        self.assertEqual(len(found), 1)

    def test_a_site_an_earlier_walk_stepped_over_starts_nothing(self):
        rom = bytes(0x40) + assembled(NARROW, STORE_DATA, LOAD_DATA, RETURN) + bytes(0x40)

        found = conversation.shapes(rom, WINDOW)

        self.assertEqual(sum(found.values()), 1)
        self.assertEqual(len(conversation.sites(rom, WINDOW)), 2)

    def test_the_same_shape_twice_is_counted_rather_than_repeated(self):
        one = assembled(NARROW, STORE_DATA, RETURN)
        rom = bytes(0x40) + one + bytes(0x40) + one + bytes(0x40)

        found = conversation.shapes(rom, WINDOW)

        self.assertEqual(sum(found.values()), len(conversation.sites(rom, WINDOW)))


if __name__ == "__main__":
    unittest.main()
