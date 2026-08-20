"""Read the driver routine in every cartridge present, and report what it says.

The unit tests build small routines by hand and check that each instruction is
read the way it should be. That proves the reader, not the reading. What proves
the reading is a real cartridge, because a real driver was written by somebody
who had the part on a desk and had to make it work.

So this walks every cartridge on disk, finds the code that drives the part, and
prints the exchange it has with it. A cartridge is confirmed against four digests
before a byte of it is disassembled: a file that is not the one named would be
read anyway and would report a protocol nobody's hardware has, which is worse
than reporting nothing at all.

Nothing here is a pass against a recorded answer. What a cartridge says to its
part is the evidence, and this exists to produce it rather than to agree with
something written down earlier. It fails only when a cartridge that should have a
driver turns out to have none, which means the reader stopped seeing something it
used to see.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "snes-mapper-python"))
sys.path.insert(0, str(ROOT / "conformance"))

from mapper import header

import cartridges
from snesdriver import conversation, windows

PART = "dsp"

SHOWN = 4
"""How many of a cartridge's shapes a report prints."""

WHY_NOT = cartridges.WHY_NOT


class Reading:
    """What one cartridge turned out to say to its part."""

    def __init__(self, identity, layout, sites, shapes):
        self.identity = identity
        self.layout = layout
        self.sites = sites
        self.shapes = shapes

    @property
    def speaks(self):
        return bool(self.shapes)

    def __repr__(self):
        return f"<Reading {self.identity.name}, {len(self.shapes)} shapes>"


def read(image, identity, part=PART):
    """What one cartridge says to that part, or nothing if it has no window."""
    found = header.read(image)
    window = windows.window_for(part, found.layout)
    if window is None:
        return Reading(identity, found.layout, (), {})
    return Reading(
        identity,
        found.layout,
        conversation.sites(image, window),
        conversation.shapes(image, window),
    )


def sweep(where=None, catalogue=None, part=PART):
    """Every cartridge present, read."""
    return [
        read(path.read_bytes(), identity, part)
        for identity, path in cartridges.found(where, catalogue)
    ]


def report(readings):
    """The lines a person reads, one cartridge at a time."""
    lines = []
    for reading in readings:
        lines.append(
            f"  {reading.identity.name}: {reading.layout},"
            f" {len(reading.sites)} sites, {len(reading.shapes)} shapes"
        )
        for shape, count in sorted(reading.shapes.items(), key=lambda held: -held[1])[:SHOWN]:
            lines.append(f"      x{count} {shape}")
    return lines


def silent(readings):
    """Every cartridge that turned out to say nothing to the part."""
    return [reading for reading in readings if not reading.speaks]


def main(argv, catalogue=None):
    where = Path(argv[0]) if argv else None
    readings = sweep(where, catalogue)

    if not readings:
        print(f"  no cartridge was found under {where or cartridges.directory()}")
        print(f"  {WHY_NOT}")
        return 2

    for line in report(readings):
        print(line)

    quiet = silent(readings)
    print(f"  {len(readings)} cartridges read, {len(quiet)} said nothing to the {PART}")
    for reading in quiet:
        print(f"    silent: {reading.identity.name} ({reading.layout})")
    return 1 if quiet else 0


def command():
    """The installed console command, which takes its arguments from the shell."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    command()
