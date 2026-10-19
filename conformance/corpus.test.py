import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import cartridges, corpus, corroborate, traced

DIGEST = "ab" * 32


def a_site(offset: str, widths: list[int], disputed: bool = False) -> dict[str, Any]:
    return {"offset": offset, "widths": widths, "disputed": disputed}


def a_corpus(*sites: dict[str, Any]) -> dict[str, Any]:
    return {"cartridges": {DIGEST: {"sites": list(sites)}}}


class WidthsTest(unittest.TestCase):
    def test_a_site_traced_at_one_width_gives_that_width(self) -> None:
        # Arrange
        held = a_corpus(a_site("0x00702a", [2]))

        # Act
        found = corpus.widths(DIGEST, held)

        # Assert
        self.assertEqual(found, {0x702A: 2})

    def test_a_site_traced_at_two_widths_gives_none(self) -> None:
        # Arrange
        held = a_corpus(a_site("0x00702a", [1, 2]))

        # Act
        found = corpus.widths(DIGEST, held)

        # Assert
        self.assertEqual(found, {})

    def test_a_site_whose_decode_disagreed_once_gives_none(self) -> None:
        # Arrange
        held = a_corpus(a_site("0x00702a", [1], disputed=True))

        # Act
        found = corpus.widths(DIGEST, held)

        # Assert
        self.assertEqual(found, {})

    def test_a_cartridge_never_traced_gives_none(self) -> None:
        # Arrange
        held = a_corpus(a_site("0x00702a", [1]))

        # Act
        found = corpus.widths("cd" * 32, held)

        # Assert
        self.assertEqual(found, {})


class LoadTest(unittest.TestCase):
    def test_a_corpus_is_read_from_the_file_named(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "traced.json"
        path.write_text(json.dumps(a_corpus(a_site("0x000100", [1]))))

        # Act
        found = corpus.load(path)

        # Assert
        self.assertEqual(corpus.widths(DIGEST, found), {0x100: 1})

    def test_a_missing_file_is_a_corpus_holding_no_cartridge(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "absent.json"

        # Act
        found = corpus.load(path)

        # Assert
        self.assertEqual(found, {"cartridges": {}})

    def test_the_committed_corpus_is_read_when_none_is_named(self) -> None:
        # Arrange
        expected = json.loads(corpus.PATH.read_text())

        # Act
        found = corpus.load()

        # Assert
        self.assertEqual(found, expected)

    def test_and_answers_for_a_cartridge_when_none_is_named(self) -> None:
        # Arrange
        held = corpus.load()

        # Act
        found = {digest: corpus.widths(digest) for digest in held["cartridges"]}

        # Assert
        self.assertEqual(
            found, {digest: corpus.widths(digest, held) for digest in held["cartridges"]}
        )


def implied_widths(site: dict[str, Any]) -> list[int]:
    by_index = site["mnemonic"] in corroborate.SIZED_BY_INDEX
    return sorted({1 if flags[1 if by_index else 0] else 2 for flags in site["flags"]})


class CommittedCorpusTest(unittest.TestCase):
    def test_every_cartridge_traced_is_one_the_manifest_names(self) -> None:
        # Arrange
        named = {entry["sha256"] for entry in cartridges.manifest()["cartridges"]}

        # Act
        traced_ones = set(corpus.load()["cartridges"])

        # Assert
        self.assertEqual(traced_ones - named, set())

    def test_every_record_stands_on_the_emulator_rung_and_names_its_runs(self) -> None:
        # Arrange
        expected = [(run.name, run.frames) for run in traced.RUNS]

        # Act
        records = list(corpus.load()["cartridges"].values())

        # Assert
        self.assertEqual(
            {
                (
                    record["rung"],
                    record["emulator"].split()[0],
                    str([(run["input"], run["frames"]) for run in record["runs"]]),
                )
                for record in records
            },
            {("emulator", "MAME", str(expected))},
        )

    def test_every_site_moved_the_width_its_opcode_moves_under_the_flags_it_held(self) -> None:
        # Arrange
        sites = [one for record in corpus.load()["cartridges"].values() for one in record["sites"]]

        # Act
        wrong = [one for one in sites if implied_widths(one) != one["widths"]]

        # Assert
        self.assertEqual((wrong, len(sites) > 0), ([], True))

    def test_a_site_settles_a_width_only_when_it_held_one_and_was_never_disputed(self) -> None:
        # Arrange
        held = corpus.load()

        # Act
        settled = {digest: corpus.widths(digest, held) for digest in held["cartridges"]}

        # Assert
        self.assertEqual(
            {
                digest: {
                    int(one["offset"], 16): one["widths"][0]
                    for one in record["sites"]
                    if len(one["widths"]) == 1 and not one["disputed"]
                }
                for digest, record in held["cartridges"].items()
            },
            settled,
        )


if __name__ == "__main__":
    unittest.main()
