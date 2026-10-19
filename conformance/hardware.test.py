import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver

HARDWARE = Path(__file__).resolve().parent / "hardware.json"


def declared() -> dict[str, Any]:
    held = json.loads(HARDWARE.read_text())
    assert isinstance(held, dict), f"{HARDWARE} does not hold an object"
    return held


def declared_banks(row: dict[str, Any]) -> list[int]:
    ranges = [row["banks"], *([row["mirrorBanks"]] if "mirrorBanks" in row else [])]
    return [int(one, 16) for pair in ranges for one in pair]


def declared_register(row: dict[str, Any], bank: int, address: int) -> str | None:
    edges = declared_banks(row)
    if not any(edges[at] <= bank <= edges[at + 1] for at in range(0, len(edges), 2)):
        return None
    if int(row["status"], 16) <= address <= int(row["statusEnd"], 16):
        return "status"
    if int(row["data"], 16) <= address <= int(row["end"], 16):
        return "data"
    return None


def probes(row: dict[str, Any]) -> list[tuple[int, int]]:
    edges = [int(row[name], 16) for name in ("data", "status", "end", "statusEnd")]
    banks = declared_banks(row)
    addresses = {one + step for one in edges for step in (-1, 0, 1)}
    returned = {one + step for one in banks for step in (-1, 0, 1)}
    return [
        (bank, address)
        for bank in sorted(returned)
        for address in sorted(addresses)
        if 0 <= bank <= 0xFF and 0 <= address <= 0xFFFF
    ]


def misread(row: dict[str, Any]) -> list[tuple[int, int]]:
    window = snesdriver.window_for(row["part"], row["layout"])
    assert window is not None, f"{row['part']}/{row['layout']} is declared and not known"
    return [
        (bank, address)
        for bank, address in probes(row)
        if window.reaches(bank, address) != declared_register(row, bank, address)
    ]


class DocumentTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.declared = declared()

    def test_the_authority_puts_the_manual_first_and_the_cartridge_after_it(self) -> None:
        # Arrange
        order = self.declared["authority"]["order"]

        # Act
        found = ("Book II" in order[0], "the cartridge" in order[1])

        # Assert
        self.assertEqual(found, (True, True))

    def test_it_says_which_windows_no_document_covers(self) -> None:
        # Arrange
        missing = self.declared["authority"]["whatIsMissing"]

        # Act
        named = [part for part in ("ST010", "ST011", "ST018", "OBC1") if part in missing]

        # Assert
        self.assertEqual(named, ["ST010", "ST011", "ST018", "OBC1"])

    def test_what_no_evidence_covers_is_recorded_rather_than_filled_in(self) -> None:
        stated = self.declared["notStated"]

        self.assertGreaterEqual(len(stated), 4)

    def test_every_window_says_whether_it_is_verified(self) -> None:
        missing = [
            f"{row['part']}/{row['layout']}"
            for row in self.declared["windows"]
            if "verified" not in row
        ]

        self.assertEqual(missing, [])

    def test_only_the_windows_book_ii_prints_claim_to_be_documented(self) -> None:
        # Arrange
        rows = self.declared["windows"]

        # Act
        claimed = [
            (row["part"], row["layout"], row.get("document")) for row in rows if row["verified"]
        ]

        # Assert
        self.assertEqual(
            claimed,
            [
                ("dsp", "lorom", "developmentManualBookIIScan"),
                ("dsp", "hirom", "developmentManualBookIIScan"),
            ],
        )

    def test_and_each_holds_the_figure_s_ranges(self) -> None:
        # Arrange
        rows = [row for row in self.declared["windows"] if row["verified"]]

        # Act
        found = [
            {
                cell["register"].split()[0].lower(): (
                    int(cell["from"][:-1], 16),
                    int(cell["to"][:-1], 16),
                )
                for cell in row["rows"]
            }
            for row in rows
        ]

        # Assert
        self.assertEqual(
            found,
            [
                {
                    "status": (int(row["status"], 16), int(row["statusEnd"], 16)),
                    "data": (int(row["data"], 16), int(row["end"], 16) + 1),
                }
                for row in rows
            ],
        )

    def test_every_window_names_its_evidence_and_what_would_settle_it(self) -> None:
        missing = [
            f"{row['part']}/{row['layout']}"
            for row in self.declared["windows"]
            if not (row.get("evidence") and row.get("howToSettleIt"))
        ]

        self.assertEqual(missing, [])


class TableTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.rows: list[dict[str, Any]] = declared()["windows"]

    def test_every_declared_window_is_one_this_package_knows(self) -> None:
        # Arrange
        rows = self.rows

        # Act
        missing = [
            f"{row['part']}/{row['layout']}"
            for row in rows
            if snesdriver.window_for(row["part"], row["layout"]) is None
        ]

        # Assert
        self.assertEqual(missing, [])

    def test_and_every_window_this_package_knows_is_declared(self) -> None:
        # Arrange
        declared_pairs = {(row["part"], row["layout"]) for row in self.rows}

        # Act
        known = {
            (part, layout) for part, layouts in snesdriver.WINDOWS.items() for layout in layouts
        }

        # Assert
        self.assertEqual(known - declared_pairs, set())

    def test_every_declared_edge_is_where_the_window_answers(self) -> None:
        # Arrange
        rows = self.rows

        # Act
        wrong = {f"{row['part']}/{row['layout']}": found for row in rows if (found := misread(row))}

        # Assert
        self.assertEqual(wrong, {})

    def test_the_probes_cross_every_declared_edge(self) -> None:
        # Arrange
        row = next(one for one in self.rows if (one["part"], one["layout"]) == ("dsp", "lorom"))

        # Act
        found = probes(row)

        # Assert
        self.assertEqual(
            (len(found), found[0], found[-1], (0x30, 0xBFFF) in found, (0xAF, 0xC000) in found),
            (12 * 9, (0x2F, 0x7FFF), (0xC0, 0xFFFF), True, True),
        )

    def test_the_select_bit_is_the_one_that_separates_data_from_status(self) -> None:
        wrong = [
            (row["part"], row["layout"])
            for row in self.rows
            if row["selectBit"] is not None
            and int(row["data"], 16) ^ int(row["status"], 16) != 1 << row["selectBit"]
        ]

        self.assertEqual(wrong, [])

    def test_a_window_with_no_single_line_says_what_decodes_it_instead(self) -> None:
        silent = [
            (row["part"], row["layout"])
            for row in self.rows
            if row["selectBit"] is None and "one line" not in row["selectedBy"].lower()
        ]

        self.assertEqual(silent, [])

    def test_and_every_window_says_which_of_the_two_it_is(self) -> None:
        missing = [row["part"] for row in self.rows if not row.get("selectedBy")]

        self.assertEqual(missing, [])

    def test_the_same_part_uses_a_different_bit_under_a_different_layout(self) -> None:
        by_layout = {row["layout"]: row["selectBit"] for row in self.rows if row["part"] == "dsp"}

        self.assertNotEqual(by_layout["lorom"], by_layout["hirom"])

    def test_which_is_why_a_window_is_looked_up_by_part_and_layout_together(self) -> None:
        claim = declared()["decode"]["claim"]

        self.assertIn("window rather than at one address", claim)

    def test_and_that_claim_is_marked_undocumented_too(self) -> None:
        decode = declared()["decode"]

        self.assertEqual((decode["verified"], bool(decode["howToSettleIt"])), (False, True))


class DivergenceTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        here = Path(__file__).resolve().parent
        self.entries: list[dict[str, Any]] = json.loads((here / "divergences.json").read_text())[
            "divergences"
        ]

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        allowed = {"cartridges", "document", "reference", "neither"}

        self.assertEqual({entry["packageFollows"] for entry in self.entries} - allowed, set())

    def test_each_entry_says_what_would_settle_it(self) -> None:
        missing = [entry["id"] for entry in self.entries if not entry.get("wouldSettleIt")]

        self.assertEqual(missing, [])

    def test_the_absence_of_a_document_is_the_first_entry(self) -> None:
        self.assertEqual(self.entries[0]["id"], "no-document-for-any-window")

    def test_an_emulator_agreeing_is_recorded_as_not_corroboration(self) -> None:
        entry = next(
            item
            for item in self.entries
            if item["id"] == "an-emulator-is-not-a-second-witness-here"
        )

        self.assertIn("same cartridge code", entry["reasoning"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
