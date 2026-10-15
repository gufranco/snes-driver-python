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

WHY_NOT = cartridges.WHY_NOT


class Reading:
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
    return [
        read(path.read_bytes(), identity, part)
        for identity, path in cartridges.found(where, catalogue)
    ]


def report(readings: Sequence[Reading]) -> list[str]:
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
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    command()
