"""How fast a routine is walked, and a floor it must not fall through.

Not a benchmark for its own sake. Walking a routine is the call every other
question here is built on, and a sweep over a library walks a hundred and
twenty sites per cartridge across dozens of cartridges. The way that stops being
usable is gradual: a decode grows an allocation, a width test becomes a
comprehension, and a year later a sweep nobody changed takes an hour. A floor
that fails loudly is cheaper than noticing.

The routine measured is short and synthetic, and deliberately so. A real one
comes out of a cartridge, and a floor that needed a cartridge on the machine
would be a floor that never runs on a hosted runner.

The floor is deliberately far below what the walk does today. It is there to
catch something several times slower, not to police the noise between one runner
and another, because a shared runner's variance is larger than any change worth
arguing about.

Every figure is a median across repeats rather than a mean, because one
scheduling hiccup moves a mean and moves a median much less, and the runtime
version is printed beside it because it is the single thing that changes these
numbers most.

Run it outside the coverage step. A tracer costs about ten times what this does,
so a floor measured under one measures the tracer.
"""

from __future__ import annotations

import statistics
import sys
import time
from typing import TYPE_CHECKING

from snesdriver import walk

if TYPE_CHECKING:
    from collections.abc import Sequence

FLOOR = 20_000
"""Routines per second this must beat, an order of magnitude below what it does."""

CALLS = 20_000
"""Routines per repeat. Enough that the host's timer resolution does not decide."""

REPEATS = 5
"""How many repeats the median is taken across."""

ROUTINE = bytes([0xE2, 0x20, 0xA9, 0x00, 0x8F, 0x00, 0x80, 0x30, 0x60])
"""Set the accumulator narrow, load, store long, return.

Short, and it exercises the part that cannot be skipped: the width of the store
is not in the store, it was set by the instruction before it. A routine without
that would be timing a decode rather than a walk.
"""

IMAGE = ROUTINE + bytes(1024)
"""The routine with room after it, so the walk ends where the routine does."""


class Timed:
    """One measured run, and what it is allowed to say about itself."""

    __slots__ = ("calls", "seconds", "what")

    def __init__(self, what: str, calls: int, seconds: Sequence[float]) -> None:
        self.what = what
        self.calls = calls
        self.seconds = list(seconds)

    def median(self) -> float:
        return statistics.median(self.seconds)

    def rate(self) -> float:
        """Calls per second, or zero when the clock could not see the work.

        A run that measured zero seconds is a reading about the clock rather
        than about the code, and reporting it as unbounded speed would let a
        machine with a coarse timer pass a floor it never met.
        """
        taken = self.median()
        return self.calls / taken if taken > 0 else 0.0

    def beats(self, floor: int) -> bool:
        return self.rate() >= floor


def measure(calls: int = CALLS, repeats: int = REPEATS) -> Timed:
    """Walk the same routine over and over, carrying the width through, and time it."""
    seconds = []
    for _ in range(repeats):
        started = time.perf_counter()
        for _ in range(calls):
            list(walk.through(IMAGE, 0))
        seconds.append(time.perf_counter() - started)
    return Timed("walk", calls, seconds)


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
    """What the run reports, whether it passed or not."""
    runtime = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    lines = [
        f"  {found.what}: {found.rate():,.0f} per second"
        f" (median of {len(found.seconds)}) on Python {runtime}",
        f"  floor: {floor:,} per second",
    ]
    if not found.beats(floor):
        lines.append(f"  below the floor: {found.rate():,.0f} is under {floor:,}")
    return lines


def main(calls: int = CALLS, repeats: int = REPEATS, floor: int = FLOOR) -> int:
    found = measure(calls, repeats)
    for line in lines_for(found, floor):
        print(line)
    return 0 if found.beats(floor) else 1


if __name__ == "__main__":
    raise SystemExit(main())
