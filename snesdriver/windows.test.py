import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesdriver import windows
from snesdriver.errors import UnknownPart


class CatalogueTest(unittest.TestCase):
    def test_the_package_knows_where_several_parts_answer(self) -> None:
        self.assertIn("dsp", windows.WINDOWS)

    def test_every_part_names_a_window_for_at_least_one_layout(self) -> None:
        for part, layouts in windows.WINDOWS.items():
            self.assertTrue(layouts, part)

    def test_every_window_puts_its_data_below_its_status(self) -> None:
        for part, layouts in windows.WINDOWS.items():
            for layout, window in layouts.items():
                self.assertLess(window.data, window.status, (part, layout))

    def test_every_window_names_the_banks_it_answers_in(self) -> None:
        for layouts in windows.WINDOWS.values():
            for window in layouts.values():
                self.assertLessEqual(window.first_bank, window.last_bank)

    def test_the_seta_parts_answer_in_two_places_rather_than_one(self) -> None:
        self.assertEqual(sorted(windows.WINDOWS["st"]), ["lorom", "lorom-shared"])

    def test_the_shared_window_sits_above_the_port_window(self) -> None:
        port = windows.WINDOWS["st"]["lorom"]
        shared = windows.WINDOWS["st"]["lorom-shared"]

        self.assertGreater(shared.first_bank, port.last_bank)

    def test_the_control_pair_reads_as_status_in_the_shared_window(self) -> None:
        shared = windows.WINDOWS["st"]["lorom-shared"]

        self.assertEqual(
            [shared.reaches(0x68, at) for at in (0x0000, 0x0010, 0x0020, 0x0021)],
            [windows.DATA, windows.DATA, windows.STATUS, windows.STATUS],
        )

    def test_the_shared_window_covers_every_bank_the_part_mirrors_into(self) -> None:
        shared = windows.WINDOWS["st"]["lorom-shared"]

        self.assertEqual(
            [shared.reaches(bank, 0x0020) for bank in (0x67, 0x68, 0x6F, 0x70)],
            [None, windows.STATUS, windows.STATUS, None],
        )

    def test_the_sprite_remapper_answers_in_the_low_banks(self) -> None:
        window = windows.WINDOWS["obc1"]["lorom"]

        self.assertEqual((window.first_bank, window.last_bank), (0x00, 0x3F))

    def test_its_register_file_is_the_top_of_its_window(self) -> None:
        window = windows.WINDOWS["obc1"]["lorom"]

        self.assertEqual(
            [window.reaches(0x00, at) for at in (0x5FFF, 0x6000, 0x7FEF, 0x7FF0, 0x7FFF)],
            [None, windows.DATA, windows.DATA, windows.STATUS, windows.STATUS],
        )

    def test_a_window_prints_as_the_range_it_covers(self) -> None:
        printed = repr(windows.WINDOWS["dsp"]["lorom"])

        self.assertIn("8000", printed)


class ReachTest(unittest.TestCase):
    def test_an_address_inside_the_data_range_is_data(self) -> None:
        window = windows.WINDOWS["dsp"]["lorom"]

        self.assertEqual(window.reaches(0x30, 0x8000), windows.DATA)

    def test_an_address_inside_the_status_range_is_status(self) -> None:
        window = windows.WINDOWS["dsp"]["lorom"]

        self.assertEqual(window.reaches(0x30, 0xC000), windows.STATUS)

    def test_the_last_address_of_each_range_still_counts(self) -> None:
        window = windows.WINDOWS["dsp"]["lorom"]

        self.assertEqual(window.reaches(0x3F, 0xBFFF), windows.DATA)
        self.assertEqual(window.reaches(0x3F, 0xFFFF), windows.STATUS)

    def test_a_bank_outside_the_range_reaches_nothing(self) -> None:
        window = windows.WINDOWS["dsp"]["lorom"]

        self.assertIsNone(window.reaches(0x10, 0x8000))

    def test_and_an_address_below_the_window_reaches_nothing(self) -> None:
        window = windows.WINDOWS["dsp"]["lorom"]

        self.assertIsNone(window.reaches(0x30, 0x7FFF))

    def test_the_high_layout_answers_lower_in_the_bank(self) -> None:
        window = windows.WINDOWS["dsp"]["hirom"]

        self.assertEqual(window.reaches(0x00, 0x6000), windows.DATA)
        self.assertEqual(window.reaches(0x00, 0x7000), windows.STATUS)


class ChoosingTest(unittest.TestCase):
    def test_a_layout_the_part_has_a_window_for_is_found(self) -> None:
        self.assertIsNotNone(windows.window_for("dsp", "lorom"))

    def test_a_layout_it_has_none_for_answers_nothing(self) -> None:
        self.assertIsNone(windows.window_for("dsp", "exhirom"))

    def test_a_part_it_does_not_know_is_refused(self) -> None:
        with self.assertRaises(UnknownPart):
            windows.window_for("nonsense", "lorom")

    def test_the_parts_it_knows_are_listed_in_the_refusal(self) -> None:
        with self.assertRaises(UnknownPart) as raised:
            windows.window_for("nonsense", "lorom")

        self.assertIn("dsp", str(raised.exception))


class GuessingTest(unittest.TestCase):
    def test_a_part_with_no_window_for_the_layout_is_passed_over(self) -> None:
        reaches = [(0x00, 0x6000)] * 5

        self.assertEqual(windows.busiest("hirom", reaches), "dsp")

    def test_the_busiest_window_in_a_run_of_addresses_is_the_one_chosen(self) -> None:
        reaches = [(0x30, 0x8000)] * 20 + [(0x00, 0x2140)] * 3

        self.assertEqual(windows.busiest("lorom", reaches), "dsp")

    def test_a_run_that_reaches_no_window_chooses_nothing(self) -> None:
        self.assertIsNone(windows.busiest("lorom", [(0x00, 0x2140)] * 5))

    def test_and_an_empty_run_chooses_nothing(self) -> None:
        self.assertIsNone(windows.busiest("lorom", []))


if __name__ == "__main__":
    unittest.main()
