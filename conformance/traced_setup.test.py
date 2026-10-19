import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import corpus, traced


class SetupTest(unittest.TestCase):
    def test_the_environment_names_the_firmware_and_the_rom_path(self) -> None:
        # Arrange
        environment = {traced.FIRMWARE_VARIABLE: "/some/firmware", traced.ROMPATH_VARIABLE: "/r"}

        # Act
        setup = traced.Setup.from_environment(environment)

        # Assert
        self.assertEqual((setup.firmware, setup.rompath), (Path("/some/firmware"), "/r"))

    def test_and_names_neither_when_it_holds_neither(self) -> None:
        # Arrange
        environment: dict[str, str] = {}

        # Act
        setup = traced.Setup.from_environment(environment)

        # Assert
        self.assertEqual((setup.firmware, setup.rompath, setup.corpus), (None, None, corpus.PATH))

    def test_the_process_environment_is_read_when_none_is_given(self) -> None:
        # Arrange
        expected = os.environ.get(traced.FIRMWARE_VARIABLE)

        # Act
        setup = traced.Setup.from_environment()

        # Assert
        self.assertEqual(setup.firmware, Path(expected) if expected else None)


class FirmwareTest(unittest.TestCase):
    def test_each_cartridge_gets_the_firmware_its_part_ran(self) -> None:
        # Arrange
        names = [
            ("Dungeon Master (USA).sfc", "dsp"),
            ("SD Gundam GX (Japan).sfc", "dsp"),
            ("Top Gear 3000 (USA).sfc", "dsp"),
            ("Pilotwings (USA).sfc", "dsp"),
            ("Hayazashi Nidan Morita Shougi 2 (Japan).sfc", "st018"),
            ("Hayazashi Nidan Morita Shougi (Japan).sfc", "st"),
            ("F1-ROC II - Race of Champions (USA).sfc", "st"),
            ("Metal Combat - Falcon's Revenge (USA).sfc", "obc1"),
        ]

        # Act
        found = [traced.firmware_name(name, part) for name, part in names]

        # Assert
        self.assertEqual(found, ["dsp2", "dsp3", "dsp4", "dsp1b", "st018", "st011", "st010", None])

    def test_a_part_that_needs_firmware_and_has_no_name_for_it_gets_none(self) -> None:
        # Arrange
        name = "An Unknown Seta Game (Japan).sfc"

        # Act
        found = traced.firmware_name(name, "st")

        # Assert
        self.assertIsNone(found)

    def test_firmware_is_found_by_its_digest_whatever_its_file_is_called(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())
        made_up = bytes(range(256)) * 32
        (where / "dsp1b.bin").write_bytes(made_up)
        (where / "notes.txt").write_text("not firmware")
        known = {"dsp1b": hashlib.sha256(made_up).hexdigest()}

        # Act
        found = traced.firmware_in(where, known)

        # Assert
        self.assertEqual(found, {"dsp1b": where / "dsp1b.bin"})

    def test_no_directory_holds_no_firmware(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "absent"

        # Act
        found = [traced.firmware_in(where, {}), traced.firmware_in(None, {})]

        # Assert
        self.assertEqual(found, [{}, {}])


class CommandLineTest(unittest.TestCase):
    def test_every_file_the_emulator_writes_lands_in_the_run_scratch_folder(self) -> None:
        # Arrange
        scratch = Path(tempfile.mkdtemp())
        setup = traced.Setup(
            emulator=Path("/usr/bin/mame"),
            corpus=scratch / "traced.json",
            firmware=None,
            known={},
            rompath="/roms",
            timeout=1.0,
        )

        # Act
        told = traced.command(setup, scratch / "image.sfc", scratch)

        # Assert
        named = {
            flag: told[told.index(flag) + 1]
            for flag in (
                "-snapshot_directory",
                "-cfg_directory",
                "-nvram_directory",
                "-state_directory",
            )
        }
        self.assertEqual(sorted(Path(one).parent for one in named.values()), [scratch] * 4)


class RangesTest(unittest.TestCase):
    def test_a_window_is_watched_in_every_bank_and_its_mirror(self) -> None:
        # Arrange
        part, kind = "st", "lorom"

        # Act
        found = traced.ranges(part, kind).split(";")

        # Assert
        self.assertEqual((len(found), found[0], found[-1]), (32, "600000-600001", "EF0000-EF0FFF"))


if __name__ == "__main__":
    unittest.main()
