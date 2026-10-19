import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver

DATA = "data"
STATUS = "status"


def window(part: str, layout: str) -> snesdriver.Window:
    found = snesdriver.window_for(part, layout)
    assert found is not None
    return found


class CatalogueTest(unittest.TestCase):
    def test_the_package_knows_where_each_part_answers_under_each_layout(self) -> None:
        # Arrange
        catalogue = snesdriver.WINDOWS

        # Act
        found = {part: sorted(layouts) for part, layouts in catalogue.items()}

        # Assert
        self.assertEqual(
            found,
            {
                "dsp": ["hirom", "lorom"],
                "st": ["lorom", "lorom-shared"],
                "obc1": ["lorom"],
                "st018": ["lorom"],
            },
        )

    def test_the_two_register_names_are_the_strings_the_readme_gives(self) -> None:
        # Arrange
        names = (snesdriver.DATA, snesdriver.STATUS)

        # Act
        found = list(names)

        # Assert
        self.assertEqual(found, [DATA, STATUS])

    def test_the_shared_window_sits_above_the_port_window(self) -> None:
        # Arrange
        shared = window("st", "lorom-shared")

        # Act
        found = [shared.reaches(bank, 0x0000) for bank in (0x67, 0x68)]

        # Assert
        self.assertEqual(found, [None, DATA])

    def test_the_control_pair_reads_as_status_in_the_shared_window(self) -> None:
        # Arrange
        shared = window("st", "lorom-shared")

        # Act
        found = [shared.reaches(0x68, at) for at in (0x0000, 0x0010, 0x0020, 0x0021, 0x0022)]

        # Assert
        self.assertEqual(found, [DATA, DATA, STATUS, STATUS, DATA])

    def test_the_shared_window_covers_every_bank_the_part_mirrors_into(self) -> None:
        # Arrange
        shared = window("st", "lorom-shared")

        # Act
        found = [shared.reaches(bank, 0x0020) for bank in (0x67, 0x68, 0x6F, 0x70)]

        # Assert
        self.assertEqual(found, [None, STATUS, STATUS, None])

    def test_the_sprite_remapper_answers_in_the_low_banks(self) -> None:
        # Arrange
        remapper = window("obc1", "lorom")

        # Act
        found = [remapper.reaches(bank, 0x6000) for bank in (0x00, 0x3F, 0x40)]

        # Assert
        self.assertEqual(found, [DATA, DATA, None])

    def test_its_register_file_is_the_top_of_its_window(self) -> None:
        # Arrange
        remapper = window("obc1", "lorom")

        # Act
        found = [remapper.reaches(0x00, at) for at in (0x5FFF, 0x6000, 0x7FEF, 0x7FF0, 0x7FFF)]

        # Assert
        self.assertEqual(found, [None, DATA, DATA, STATUS, STATUS])

    def test_a_window_prints_as_the_range_it_covers(self) -> None:
        # Arrange
        dsp = window("dsp", "lorom")

        # Act
        printed = repr(dsp)

        # Assert
        self.assertEqual(printed, "<Window $30-$3f,$b0-$bf:8000 data, c000 status>")

    def test_a_window_that_does_not_mirror_prints_one_range(self) -> None:
        # Arrange
        st018 = window("st018", "lorom")

        # Act
        printed = repr(st018)

        # Assert
        self.assertEqual(printed, "<Window $00-$3f:3800 data, 3804 status>")

    def test_the_sprite_remapper_answers_in_the_upper_banks_its_cartridge_runs_in(self) -> None:
        # Arrange
        obc1 = window("obc1", "lorom")

        # Act
        found = [obc1.reaches(bank, at) for bank in (0x80, 0xBF) for at in (0x6000, 0x7FF5)]

        # Assert
        self.assertEqual(found, [DATA, STATUS, DATA, STATUS])

    def test_a_window_built_by_hand_ends_its_status_range_where_its_data_ends(self) -> None:
        # Arrange
        built = snesdriver.Window(0x00, 0x00, 0x1000, 0x1800, 0x1FFF)

        # Act
        found = [built.reaches(0x00, at) for at in (0x17FF, 0x1800, 0x1FFF, 0x2000)]

        # Assert
        self.assertEqual(found, [DATA, STATUS, STATUS, None])


class ReachTest(unittest.TestCase):
    def test_an_address_inside_the_data_range_is_data(self) -> None:
        # Arrange
        dsp = window("dsp", "lorom")

        # Act
        found = dsp.reaches(0x30, 0x8000)

        # Assert
        self.assertEqual(found, DATA)

    def test_an_address_inside_the_status_range_is_status(self) -> None:
        # Arrange
        dsp = window("dsp", "lorom")

        # Act
        found = dsp.reaches(0x30, 0xC000)

        # Assert
        self.assertEqual(found, STATUS)

    def test_the_last_address_of_each_range_still_counts(self) -> None:
        # Arrange
        dsp = window("dsp", "lorom")

        # Act
        found = [dsp.reaches(0x3F, at) for at in (0xBFFF, 0xFFFF)]

        # Assert
        self.assertEqual(found, [DATA, STATUS])

    def test_a_bank_outside_the_range_reaches_nothing(self) -> None:
        # Arrange
        dsp = window("dsp", "lorom")

        # Act
        found = [dsp.reaches(bank, 0x8000) for bank in (0x2F, 0x40)]

        # Assert
        self.assertEqual(found, [None, None])

    def test_and_an_address_below_the_window_reaches_nothing(self) -> None:
        # Arrange
        dsp = window("dsp", "lorom")

        # Act
        found = dsp.reaches(0x30, 0x7FFF)

        # Assert
        self.assertIsNone(found)

    def test_the_dsp_answers_in_the_upper_banks_as_well(self) -> None:
        # Arrange
        windows = (window("dsp", "lorom"), window("dsp", "hirom"))

        # Act
        found = [
            (one.reaches(bank, one.data), one.reaches(bank, one.status))
            for one in windows
            for bank in (one.first_bank | 0x80, one.last_bank | 0x80)
        ]

        # Assert
        self.assertEqual(found, [(DATA, STATUS)] * 4)

    def test_and_nowhere_between_the_two_ranges(self) -> None:
        # Arrange
        dsp = window("dsp", "lorom")

        # Act
        found = [dsp.reaches(bank, 0x8000) for bank in (0x40, 0xAF, 0xC0)]

        # Assert
        self.assertEqual(found, [None, None, None])

    def test_the_high_layout_answers_lower_in_the_bank(self) -> None:
        # Arrange
        dsp = window("dsp", "hirom")

        # Act
        found = [dsp.reaches(0x00, at) for at in (0x6000, 0x7000)]

        # Assert
        self.assertEqual(found, [DATA, STATUS])


class ChoosingTest(unittest.TestCase):
    def test_a_layout_the_part_has_a_window_for_is_found(self) -> None:
        # Arrange
        expected = snesdriver.WINDOWS["dsp"]["lorom"]

        # Act
        found = snesdriver.window_for("dsp", "lorom")

        # Assert
        self.assertIs(found, expected)

    def test_a_layout_it_has_none_for_answers_nothing(self) -> None:
        # Arrange
        layout = "exhirom"

        # Act
        found = snesdriver.window_for("dsp", layout)

        # Assert
        self.assertIsNone(found)

    def test_a_part_it_does_not_know_is_refused_with_every_part_it_knows(self) -> None:
        # Arrange
        part = "nonsense"

        # Act
        with self.assertRaises(snesdriver.UnknownPart) as raised:
            snesdriver.window_for(part, "lorom")

        # Assert
        self.assertEqual(
            str(raised.exception),
            "nonsense is not a part with a known window; there are dsp, obc1, st, st018",
        )


class GuessingTest(unittest.TestCase):
    def test_a_part_with_no_window_for_the_layout_is_passed_over(self) -> None:
        # Arrange
        reaches = [(0x00, 0x6000)] * 5

        # Act
        found = snesdriver.busiest("hirom", reaches)

        # Assert
        self.assertEqual(found, "dsp")

    def test_the_busiest_window_in_a_run_of_addresses_is_the_one_chosen(self) -> None:
        # Arrange
        reaches = [(0x30, 0x8000)] * 2 + [(0x60, 0x0000)] * 3

        # Act
        found = snesdriver.busiest("lorom", reaches)

        # Assert
        self.assertEqual(found, "st")

    def test_a_run_that_reaches_no_window_chooses_nothing(self) -> None:
        # Arrange
        reaches = [(0x00, 0x2140)] * 5

        # Act
        found = snesdriver.busiest("lorom", reaches)

        # Assert
        self.assertIsNone(found)

    def test_and_an_empty_run_chooses_nothing(self) -> None:
        # Arrange
        reaches: list[tuple[int, int]] = []

        # Act
        found = snesdriver.busiest("lorom", reaches)

        # Assert
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
