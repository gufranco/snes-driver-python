import contextlib
import hashlib
import io
import json
import stat
import sys
import tempfile
import textwrap
import unittest
import zlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import corpus, traced

ROUTINE = bytes([0xE2, 0x20, 0x8F, 0x00, 0x80, 0x3F, 0x60])

AGREEING = "access write 3F8000 1 009006 30 0 00 0000 0000 0000 5 2"

WIDER_THAN_THE_FLAGS = "access write 3F8000 2 009006 30 0 00 0000 0000 0000 1 9"

FROM_NO_INSTRUCTION = "access write 3F8001 1 00F000 30 0 00 0000 0000 0000 4 3"

HEADER = "frames {frames}\ntaps 64\nwidest-pair 0.000000093122\nclosest-apart 1.000000000000\n"


def a_cartridge(chipset: int = 0x03, title: bytes = b"TRACED CARTRIDGE     ") -> bytes:
    rom = bytearray(0x100000)
    rom[0x7FC0:0x7FD5] = title
    rom[0x7FD5] = 0x20
    rom[0x7FD6] = chipset
    rom[0x7FD7] = 0x0A
    rom[0x7FD9] = 0x01
    rom[0x7FDC:0x7FE0] = bytes([0xA5, 0xA5, 0x5A, 0x5A])
    rom[0x1000 : 0x1000 + len(ROUTINE)] = ROUTINE
    return bytes(rom)


def an_entry(name: str, image: bytes) -> dict[str, Any]:
    return {
        "name": name,
        "title": "TRACED CARTRIDGE",
        "bytes": len(image),
        "layout": "lorom",
        "chipset": "0x03",
        "crc32": f"{zlib.crc32(image) & 0xFFFFFFFF:08x}",
        "md5": hashlib.md5(image).hexdigest(),
        "sha1": hashlib.sha1(image).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


def an_emulator(where: Path, lines: str = AGREEING, code: int = 0, sleep: float = 0.0) -> Path:
    path = where / "mame"
    body = f"""\
        #!{sys.executable}
        import os, sys, time
        if sys.argv[1:] == ["-version"]:
            print("0.289 (made up)")
            raise SystemExit(0)
        time.sleep({sleep})
        frames = os.environ["TRACE_FRAMES"]
        header = {HEADER!r}.format(frames=frames)
        if {code} == 0:
            with open(os.environ["TRACE_OUT"], "w") as handle:
                handle.write(header + {lines!r} + "\\n")
        raise SystemExit({code})
        """
    path.write_text(textwrap.dedent(body))
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class Library:
    def __init__(self, image: bytes | None = None, with_firmware: bool = True) -> None:
        self.where = Path(tempfile.mkdtemp())
        self.games = self.where / "games"
        self.games.mkdir()
        self.firmware = self.where / "firmware"
        self.firmware.mkdir()
        self.image = image if image is not None else a_cartridge()
        (self.games / "traced.sfc").write_bytes(self.image)
        made_up = bytes(range(256)) * 32
        if with_firmware:
            (self.firmware / "dsp1b.bin").write_bytes(made_up)
        (self.firmware / "notes.txt").write_text("not firmware")
        self.known = {"dsp1b": hashlib.sha256(made_up).hexdigest()}
        self.catalogue = {"cartridges": [an_entry("traced.sfc", self.image)]}
        self.corpus = self.where / "traced.json"
        self.digest = hashlib.sha256(self.image).hexdigest()

    def setup(self, emulator: Path | None, timeout: float = 60.0) -> traced.Setup:
        return traced.Setup(
            emulator=emulator,
            corpus=self.corpus,
            firmware=self.firmware,
            known=self.known,
            rompath=str(self.where),
            timeout=timeout,
        )

    def run(self, emulator: Path | None, timeout: float = 60.0) -> tuple[int, str]:
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            code = traced.main([str(self.games)], self.catalogue, self.setup(emulator, timeout))
        return code, said.getvalue()


class SkipTest(unittest.TestCase):
    def test_a_machine_without_the_emulator_traces_nothing_and_says_how_much(self) -> None:
        # Arrange
        library = Library()

        # Act
        code, said = library.run(None)

        # Assert
        self.assertEqual(
            (code, said.splitlines()[0]), (2, "  no mame on this machine: 1 cartridges not traced")
        )

    def test_a_directory_with_no_cartridge_says_so(self) -> None:
        # Arrange
        library = Library()
        emulator = an_emulator(library.where)
        said = io.StringIO()

        # Act
        with contextlib.redirect_stdout(said):
            code = traced.main([str(library.firmware)], library.catalogue, library.setup(emulator))

        # Assert
        self.assertEqual((code, said.getvalue().splitlines()[1]), (2, f"  {traced.WHY_NOT}"))

    def test_a_cartridge_with_no_firmware_on_hand_is_counted_and_named(self) -> None:
        # Arrange
        library = Library(with_firmware=False)

        # Act
        code, said = library.run(an_emulator(library.where))

        # Assert
        self.assertEqual(
            (code, said.splitlines()),
            (
                2,
                ["    skipped: traced.sfc, dsp1b firmware is not on hand", "  0 cartridges traced"],
            ),
        )

    def test_a_cartridge_naming_no_part_is_not_traced(self) -> None:
        # Arrange
        library = Library(a_cartridge(chipset=0x02))

        # Act
        code, said = library.run(an_emulator(library.where))

        # Assert
        self.assertEqual(
            (code, said.splitlines()[0]),
            (2, "    skipped: traced.sfc, its header names no part with a window"),
        )


class RecordTest(unittest.TestCase):
    def test_a_run_records_each_site_with_the_width_the_bus_moved(self) -> None:
        # Arrange
        library = Library()

        # Act
        code, _said = library.run(an_emulator(library.where))

        # Assert
        record = corpus.load(library.corpus)["cartridges"][library.digest]
        self.assertEqual(
            (code, record["sites"]),
            (
                0,
                [
                    {
                        "offset": "0x001002",
                        "start": "00:9002",
                        "mnemonic": "sta",
                        "mode": "absoluteLong",
                        "directions": ["write"],
                        "widths": [1],
                        "halves": ["one"],
                        "flags": [[True, True]],
                        "low": "3f8000",
                        "high": "3f8000",
                        "count": 10,
                        "first": 2,
                        "disputed": False,
                    }
                ],
            ),
        )

    def test_the_record_names_its_rung_emulator_firmware_and_runs(self) -> None:
        # Arrange
        library = Library()

        # Act
        library.run(an_emulator(library.where))

        # Assert
        record = corpus.load(library.corpus)["cartridges"][library.digest]
        self.assertEqual(
            (
                record["rung"],
                record["emulator"],
                record["firmware"],
                [(run["input"], run["frames"]) for run in record["runs"]],
            ),
            (
                "emulator",
                "MAME 0.289 (made up)",
                {"name": "dsp1b", "sha256": library.known["dsp1b"]},
                [(run.name, run.frames) for run in traced.RUNS],
            ),
        )

    def test_each_run_keeps_how_far_apart_the_bytes_it_paired_were(self) -> None:
        # Arrange
        library = Library()

        # Act
        library.run(an_emulator(library.where))

        # Assert
        run = corpus.load(library.corpus)["cartridges"][library.digest]["runs"][0]
        self.assertEqual(
            (run["widestPairSeconds"], run["closestApartSeconds"], run["schedule"]),
            (9.3122e-08, None, None),
        )

    def test_a_width_the_decode_contradicts_disputes_the_site(self) -> None:
        # Arrange
        library = Library()

        # Act
        library.run(an_emulator(library.where, f"{AGREEING}\n{WIDER_THAN_THE_FLAGS}"))

        # Assert
        record = corpus.load(library.corpus)["cartridges"][library.digest]
        self.assertEqual(
            (record["sites"][0]["disputed"], record["disagreements"][0]["reason"]),
            (True, "the bus moved 2 bytes and sta under the recorded flags moves 1"),
        )

    def test_and_a_disputed_site_settles_no_width(self) -> None:
        # Arrange
        library = Library()

        # Act
        library.run(an_emulator(library.where, f"{AGREEING}\n{WIDER_THAN_THE_FLAGS}"))

        # Assert
        self.assertEqual(corpus.widths(library.digest, corpus.load(library.corpus)), {})

    def test_an_access_no_instruction_explains_is_kept_as_a_disagreement(self) -> None:
        # Arrange
        library = Library()

        # Act
        library.run(an_emulator(library.where, FROM_NO_INSTRUCTION))

        # Assert
        record = corpus.load(library.corpus)["cartridges"][library.digest]
        self.assertEqual(
            (record["sites"], record["disagreements"]),
            (
                [],
                [
                    {
                        "pc": "00:f000",
                        "direction": "write",
                        "width": 1,
                        "flags": [True, True],
                        "low": "3f8001",
                        "high": "3f8001",
                        "count": 8,
                        "reason": "no instruction ending at the recorded PC reaches the address",
                    }
                ],
            ),
        )

    def test_a_site_only_a_disagreement_found_is_not_a_site(self) -> None:
        # Arrange
        library = Library()

        # Act
        library.run(an_emulator(library.where, WIDER_THAN_THE_FLAGS))

        # Assert
        self.assertEqual(corpus.load(library.corpus)["cartridges"][library.digest]["sites"], [])

    def test_the_summary_counts_sites_widths_and_disagreements(self) -> None:
        # Arrange
        library = Library()

        # Act
        _code, said = library.run(an_emulator(library.where))

        # Assert
        self.assertEqual(
            said.splitlines()[:2],
            [
                "  traced.sfc: dsp, 1 sites, 1 with one width, 0 disagreements",
                "  1 cartridges traced",
            ],
        )

    def test_a_second_run_replaces_the_cartridge_and_keeps_the_others(self) -> None:
        # Arrange
        library = Library()
        library.corpus.write_text(json.dumps({"cartridges": {"cd" * 32: {"sites": []}}}))

        # Act
        library.run(an_emulator(library.where))

        # Assert
        self.assertEqual(
            sorted(corpus.load(library.corpus)["cartridges"]), sorted(["cd" * 32, library.digest])
        )

    def test_the_corpus_is_written_one_site_to_a_line(self) -> None:
        # Arrange
        library = Library()

        # Act
        library.run(an_emulator(library.where))

        # Assert
        lines = library.corpus.read_text().splitlines()
        self.assertEqual(len([line for line in lines if '"offset": "0x001002"' in line]), 1)


class PartWithoutFirmwareTest(unittest.TestCase):
    def test_a_part_that_carries_no_firmware_is_traced_without_any(self) -> None:
        # Arrange
        library = Library(a_cartridge(chipset=0x25), with_firmware=False)

        # Act
        code, _said = library.run(an_emulator(library.where, FROM_NO_INSTRUCTION))

        # Assert
        record = corpus.load(library.corpus)["cartridges"][library.digest]
        self.assertEqual((code, record["part"], record["firmware"]), (0, "obc1", None))


class CommandTest(unittest.TestCase):
    def test_it_leaves_by_raising_with_the_code_the_run_returned(self) -> None:
        # Arrange
        held = sys.argv
        sys.argv = ["traced", "/nowhere/at/all"]

        # Act
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
            traced.entry()
        sys.argv = held

        # Assert
        self.assertEqual(raised.exception.code, 2)


class FailureTest(unittest.TestCase):
    def test_an_emulator_that_fails_fails_the_run(self) -> None:
        # Arrange
        library = Library()

        # Act
        code, said = library.run(an_emulator(library.where, code=3))

        # Assert
        self.assertEqual((code, said.splitlines()[0]), (1, "    failed: traced.sfc"))

    def test_an_emulator_that_never_finishes_fails_the_run(self) -> None:
        # Arrange
        library = Library()

        # Act
        code, _said = library.run(an_emulator(library.where, sleep=5.0), timeout=0.5)

        # Assert
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
