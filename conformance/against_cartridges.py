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

The two path insertions below are ordered, and the order is the whole point. This
project and the mapper each carry a package called conformance, so whichever root
sits earlier on the path decides which one `from conformance import ...` resolves
to. The dependency goes on first so that this repository's own root ends up ahead
of it. Reversed, the failure is not an import error: this project silently reads
its dependency's modules, and the symptom is a run that finds no cartridges.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

from mapper import header

from conformance import cartridges
from snesdriver import conversation, windows

PART = "dsp"

SHOWN = 4
"""How many of a cartridge's shapes a report prints."""

WHY_NOT = cartridges.WHY_NOT


class Reading:
    """What one cartridge turned out to say to its part."""

    def __init__(
        self,
        identity: Any,
        layout: str,
        sites: Sequence[int],
        shapes: Mapping[str, int],
    ) -> None:
        self.identity = identity
        self.layout = layout
        self.sites = sites
        self.shapes = shapes

    @property
    def speaks(self) -> bool:
        return bool(self.shapes)

    @override
    def __repr__(self) -> str:
        return f"<Reading {self.identity.name}, {len(self.shapes)} shapes>"


def read(image: bytes, identity: Any, part: str = PART) -> Reading:
    """What one cartridge says to that part.

    A cartridge whose layout gives that part no window reads as a reading with no
    sites and no shapes, rather than as nothing. It is a cartridge that was looked
    at and had nothing to say, which is a different fact from a cartridge that was
    never looked at, and the report distinguishes them.
    """
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


def sweep(
    where: Path | str | None = None,
    catalogue: Mapping[str, Any] | None = None,
    part: str = PART,
) -> list[Reading]:
    """Every cartridge present, read."""
    return [
        read(path.read_bytes(), identity, part)
        for identity, path in cartridges.found(where, catalogue)
    ]


def report(readings: Sequence[Reading]) -> list[str]:
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


def silent(readings: Iterable[Reading]) -> list[Reading]:
    """Every cartridge that turned out to say nothing to the part."""
    return [reading for reading in readings if not reading.speaks]


def main(argv: Sequence[str], catalogue: Mapping[str, Any] | None = None) -> int:
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


def command() -> int:
    """The installed console command, which takes its arguments from the shell."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    command()
