from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

from mapper import header

from conformance import cartridges, corpus
from snesdriver import conversation, windows

SHOWN = 4

COPROCESSORS = {0x0: "dsp", 0x2: "obc1"}

CUSTOM_CHIP = 0xF

CUSTOM_CHIPS = {0x01: "st", 0x02: "st018"}

REACHED_ONLY_BY_ABSOLUTE_ACCESS = frozenset({"st018"})

WHY_NOT = cartridges.WHY_NOT


class Reading:
    def __init__(
        self,
        identity: Any,
        layout: str,
        sites: Sequence[int],
        shapes: Mapping[str, int],
        part: str | None = None,
    ) -> None:
        self.identity = identity
        self.layout = layout
        self.sites = sites
        self.shapes = shapes
        self.part = part

    @property
    def speaks(self) -> bool:
        return bool(self.shapes)

    @override
    def __repr__(self) -> str:
        return f"<Reading {self.identity.name}, {len(self.shapes)} shapes>"


def part_of(image: bytes) -> str | None:
    found = header.read(image)
    if not found.coprocessor:
        return None
    family = found.chipset >> 4
    if family == CUSTOM_CHIP:
        return CUSTOM_CHIPS.get(image[found.at - 1])
    return COPROCESSORS.get(family)


def windows_under(part: str, layout: str) -> list[Any]:
    held = windows.WINDOWS[part]
    return [held[name] for name in sorted(held) if name.split("-")[0] == layout]


def finder(part: str) -> Any:
    return conversation.reached if part in REACHED_ONLY_BY_ABSOLUTE_ACCESS else conversation.sites


def read(
    image: bytes,
    identity: Any,
    part: str | None = None,
    traced: Mapping[int, int] | None = None,
) -> Reading:
    found = header.read(image)
    named = part if part is not None else part_of(image)
    if named is None:
        return Reading(identity, found.layout, (), {})
    find = finder(named)
    seen = traced if traced is not None else corpus.widths(identity.sha256)
    tally: collections.Counter[str] = collections.Counter()
    reached: list[int] = []
    for window in windows_under(named, found.layout):
        reached.extend(find(image, window))
        tally.update(conversation.shapes(image, window, find=find, kind=found.layout, traced=seen))
    return Reading(identity, found.layout, tuple(sorted(set(reached))), dict(tally), named)


def sweep(
    where: Path | str | None = None,
    catalogue: Mapping[str, Any] | None = None,
    part: str | None = None,
) -> list[Reading]:
    return [
        read(path.read_bytes(), identity, part)
        for identity, path in cartridges.found(where, catalogue)
    ]


def report(readings: Sequence[Reading]) -> list[str]:
    lines = []
    for reading in readings:
        lines.append(
            f"  {reading.identity.name}: {reading.part or 'no known part'} {reading.layout},"
            f" {len(reading.sites)} sites, {len(reading.shapes)} shapes"
        )
        for shape, count in sorted(reading.shapes.items(), key=lambda held: -held[1])[:SHOWN]:
            lines.append(f"      x{count} {shape}")
    return lines


def by_part(readings: Iterable[Reading]) -> list[str]:
    tally: collections.Counter[tuple[str, str]] = collections.Counter()
    for reading in readings:
        part = reading.part or "no known part"
        tally[(part, "all")] += 0
        for shape, count in reading.shapes.items():
            tally[(part, "all")] += count
            tally[(part, "unknown")] += count if conversation.UNKNOWN in shape else 0
            tally[(part, "traced")] += count if conversation.TRACED in shape else 0
    return [
        f"  {part}: {tally[(part, 'all')]} exchanges,"
        f" {tally[(part, 'unknown')]} with an unknown width,"
        f" {tally[(part, 'traced')]} with a traced one"
        for part in sorted({part for part, _kind in tally})
    ]


def silent(readings: Iterable[Reading]) -> list[Reading]:
    return [reading for reading in readings if not reading.speaks]


def main(argv: Sequence[str], catalogue: Mapping[str, Any] | None = None) -> int:
    where = Path(argv[0]) if argv else None
    readings = sweep(where, catalogue)

    if not readings:
        print(f"  no cartridge was found under {where or cartridges.directory()}")
        print(f"  {WHY_NOT}")
        return 2

    for line in [*report(readings), *by_part(readings)]:
        print(line)

    quiet = silent(readings)
    print(
        f"  {len(readings)} cartridges read,"
        f" {len(quiet)} said nothing to the part their header names"
    )
    for reading in quiet:
        print(f"    silent: {reading.identity.name} ({reading.layout})")
    return 1 if quiet else 0


def command() -> int:
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    command()
