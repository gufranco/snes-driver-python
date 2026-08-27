"""Hold the window table to the facts in hardware.json, and to their standing.

Every window this package knows was read out of cartridge code rather than out of
a document, and hardware.json says so for each one. This checks that the table in
`snesdriver/windows.py` and the file agree, and that nothing in the file has
quietly been promoted to verified without a document to promote it with.
"""

import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesdriver import windows

HARDWARE = Path(__file__).resolve().parent / "hardware.json"


def declared() -> dict[str, Any]:
    held = json.loads(HARDWARE.read_text())
    assert isinstance(held, dict), f"{HARDWARE} does not hold an object"
    return held


def _declared_edges(row: dict[str, Any]) -> tuple[int, ...]:
    """The six addresses hardware.json gives for one window."""
    return (
        int(row["banks"][0], 16),
        int(row["banks"][1], 16),
        int(row["data"], 16),
        int(row["status"], 16),
        int(row["end"], 16),
        int(row["statusEnd"], 16),
    )


def _table_edges(row: dict[str, Any]) -> tuple[int, ...]:
    """The six this package actually uses for the same window."""
    window = windows.window_for(row["part"], row["layout"])
    assert window is not None, f"{row['part']}/{row['layout']} is declared and not known"
    return (
        window.first_bank,
        window.last_bank,
        window.data,
        window.status,
        window.end,
        window.status_end,
    )


class DocumentTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.declared = declared()

    def test_the_authority_puts_the_cartridge_first(self) -> None:
        order = self.declared["authority"]["order"]

        self.assertIn("the cartridge", order[0])

    def test_it_says_which_document_would_settle_this_and_that_it_is_absent(self) -> None:
        missing = self.declared["authority"]["whatIsMissing"]

        self.assertIn("not on this machine", missing)

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

    def test_no_window_claims_to_be_documented(self) -> None:
        claimed = [row["part"] for row in self.declared["windows"] if row["verified"]]

        self.assertEqual(claimed, [])

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
        missing = [
            f"{row['part']}/{row['layout']}"
            for row in self.rows
            if windows.window_for(row["part"], row["layout"]) is None
        ]

        self.assertEqual(missing, [])

    def test_and_every_window_this_package_knows_is_declared(self) -> None:
        declared_pairs = {(row["part"], row["layout"]) for row in self.rows}

        known = {(part, layout) for part, layouts in windows.WINDOWS.items() for layout in layouts}

        self.assertEqual(known - declared_pairs, set())

    def test_every_declared_address_matches_the_table(self) -> None:
        wrong = [
            (row["part"], row["layout"], _declared_edges(row), _table_edges(row))
            for row in self.rows
            if _declared_edges(row) != _table_edges(row)
        ]

        self.assertEqual(wrong, [])

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
