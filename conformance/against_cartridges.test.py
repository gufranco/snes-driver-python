"""The checks that need real cartridges, which is why they live apart.

A skipped test contributes no coverage, so on a runner with an empty directory
every line here would read as uncovered and fail the coverage gate for a reason
that has nothing to do with the code. Keeping them in one file lets that file sit
outside the gate while everything else stays inside it.
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "snes-mapper-python"))
sys.path.insert(0, str(ROOT / "conformance"))

import against_cartridges

import cartridges

PRESENT = cartridges.present()


def a_cartridge(layout="lorom", drives=True):
    """A stand-in carrying a header and, if asked, a routine that drives a part."""
    at = 0x7FC0 if layout == "lorom" else 0xFFC0
    size = 0x100000 if layout == "lorom" else 0x200000
    rom = bytearray(size)
    rom[at : at + 21] = b"DRIVEN CARTRIDGE     "
    rom[at + 21] = 0x20 if layout == "lorom" else 0x21
    rom[at + 22] = 0x03
    rom[at + 23] = 0x0A
    rom[at + 25] = 0x01
    rom[at + 28] = 0xA5
    rom[at + 29] = 0xA5
    rom[at + 30] = 0x5A
    rom[at + 31] = 0x5A
    if drives:
        where = 0x1000
        if layout == "lorom":
            rom[where : where + 9] = bytes([0xE2, 0x20, 0x8F, 0x00, 0x80, 0x3F, 0x60, 0x00, 0x00])
        else:
            rom[where : where + 9] = bytes([0xE2, 0x20, 0x8F, 0x00, 0x60, 0x00, 0x60, 0x00, 0x00])
    return bytes(rom)


class ReadTest(unittest.TestCase):
    def test_a_cartridge_that_drives_a_part_reports_a_shape(self):
        found = against_cartridges.read(a_cartridge(), _an_identity())

        self.assertTrue(found.speaks)

    def test_and_one_that_does_not_reports_none(self):
        found = against_cartridges.read(a_cartridge(drives=False), _an_identity())

        self.assertFalse(found.speaks)

    def test_the_layout_the_header_declares_is_reported(self):
        found = against_cartridges.read(a_cartridge(), _an_identity())

        self.assertEqual(found.layout, "lorom")

    def test_a_high_cartridge_is_read_at_its_own_window(self):
        found = against_cartridges.read(a_cartridge(layout="hirom"), _an_identity())

        self.assertTrue(found.speaks)

    def test_a_layout_with_no_window_for_the_part_reports_nothing(self):
        found = against_cartridges.read(a_cartridge(layout="hirom"), _an_identity(), part="st")

        self.assertFalse(found.speaks)
        self.assertEqual(found.sites, ())

    def test_a_reading_prints_as_the_cartridge_and_what_it_found(self):
        found = against_cartridges.read(a_cartridge(), _an_identity())

        self.assertIn("made-up.sfc", repr(found))


class ReportTest(unittest.TestCase):
    def test_every_cartridge_makes_a_line(self):
        readings = [against_cartridges.read(a_cartridge(), _an_identity())]

        self.assertTrue(against_cartridges.report(readings))

    def test_a_line_names_the_cartridge_and_its_layout(self):
        readings = [against_cartridges.read(a_cartridge(), _an_identity())]

        line = against_cartridges.report(readings)[0]

        self.assertIn("made-up.sfc", line)
        self.assertIn("lorom", line)

    def test_a_cartridge_saying_nothing_is_listed_as_silent(self):
        readings = [against_cartridges.read(a_cartridge(drives=False), _an_identity())]

        self.assertEqual(len(against_cartridges.silent(readings)), 1)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.where = Path(tempfile.mkdtemp())

    def _supply(self, drives=True):
        import hashlib
        import zlib

        image = a_cartridge(drives=drives)
        (self.where / "made-up.sfc").write_bytes(image)
        return {
            "cartridges": [
                {
                    "name": "made-up.sfc",
                    "title": "DRIVEN CARTRIDGE",
                    "bytes": len(image),
                    "layout": "lorom",
                    "chipset": "0x03",
                    "crc32": f"{zlib.crc32(image) & 0xFFFFFFFF:08x}",
                    "md5": hashlib.md5(image).hexdigest(),
                    "sha1": hashlib.sha1(image).hexdigest(),
                    "sha256": hashlib.sha256(image).hexdigest(),
                }
            ]
        }

    def test_a_directory_with_no_cartridge_says_so(self):
        self.assertEqual(against_cartridges.main([str(self.where)]), 2)

    def test_a_cartridge_that_speaks_is_reported_and_passes(self):
        catalogue = self._supply()
        readings = against_cartridges.sweep(self.where, catalogue)

        self.assertEqual(len(readings), 1)
        self.assertTrue(readings[0].speaks)
        self.assertTrue(against_cartridges.report(readings))

    def test_a_cartridge_that_says_nothing_is_a_failure(self):
        catalogue = self._supply(drives=False)
        readings = against_cartridges.sweep(self.where, catalogue)

        self.assertEqual(len(against_cartridges.silent(readings)), 1)

    def test_a_run_over_a_speaking_cartridge_reports_success(self):
        catalogue = self._supply()

        self.assertEqual(against_cartridges.main([str(self.where)], catalogue), 0)

    def test_and_a_run_over_a_silent_one_reports_failure(self):
        catalogue = self._supply(drives=False)

        self.assertEqual(against_cartridges.main([str(self.where)], catalogue), 1)


@unittest.skipUnless(PRESENT, cartridges.WHY_NOT)
class OnDiskTest(unittest.TestCase):
    def test_every_cartridge_on_disk_is_read(self):
        self.assertEqual(len(against_cartridges.sweep()), len(PRESENT))

    def test_every_one_of_them_says_something_to_the_part(self):
        quiet = [one.identity.name for one in against_cartridges.silent(against_cartridges.sweep())]

        self.assertEqual(quiet, [])

    def test_the_library_is_the_whole_one_rather_than_a_handful(self):
        self.assertGreater(len(PRESENT), 30)

    def test_at_least_one_cartridge_polls_before_it_reads(self):
        polling = [
            one
            for one in against_cartridges.sweep()
            if any("poll" in shape and "read" in shape for shape in one.shapes)
        ]

        self.assertTrue(polling)


def _an_identity():
    return cartridges.Identity(
        "made-up.sfc", "DRIVEN CARTRIDGE", 0x100000, "lorom", "0x03", "0" * 64
    )


if __name__ == "__main__":
    unittest.main()
