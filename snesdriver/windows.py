"""Where each part answers, and which half of its window is which.

A Super Nintendo coprocessor has no bus of its own. It appears inside the
cartridge's address space, usually as two large ranges: one the console reads and
writes to move data, and one it reads to find out whether the part is ready. The
ranges are large because the cartridge decodes only a few address lines, so every
address in a sixteen kilobyte span reaches the same register.

Which lines those are depends on the layout the cartridge declares, not on the
part. The same DSP answers at one place in a low cartridge and another in a high
one, and the line that picks between its two registers is address bit 14 in the
first case and bit 12 in the second. That is why a window is looked up by part and
layout together rather than by part alone.

The ranges here are the ones a cartridge that runs on real hardware decodes.

The Seta parts have two windows rather than one, because address bit 19 decides
which. Below it the console reaches a two byte port; above it, the four kilobyte
memory both sides share, where the parameters go in, the answer comes back, and
two bytes near the bottom act as the control pair. A layout name carries the
second window because a window is looked up by part and layout, and there is no
third thing to look one up by.

Measured, rather than assumed: with only the port window, the two cartridges
carrying an ST010 yield one exchange each. With the shared window they yield
eighteen across eight shapes, and the Japanese and American releases agree on
every one, which is what two builds of one driver routine should do.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from .errors import UnknownPart

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

DATA = "data"

STATUS = "status"


class Window:
    """One part's two ranges, in the banks it answers in.

    The status range is looked at first, which is what lets it sit inside the
    data range rather than after it. On the DSP the two ranges are adjacent and
    the order changes nothing. On the Seta parts the control pair is two bytes in
    the middle of four kilobytes of shared memory, and a window that stopped at
    the pair would report every access above it as reaching nothing.

    `status_end` is where the status range stops, and defaults to `end` so the
    adjacent case keeps spelling itself with four bounds.
    """

    __slots__ = ("data", "end", "first_bank", "last_bank", "status", "status_end")

    def __init__(
        self,
        first_bank: int,
        last_bank: int,
        data: int,
        status: int,
        end: int,
        status_end: int | None = None,
    ) -> None:
        self.first_bank = first_bank
        self.last_bank = last_bank
        self.data = data
        self.status = status
        self.end = end
        self.status_end = end if status_end is None else status_end

    def reaches(self, bank: int, address: int) -> str | None:
        """Which register an access lands on, or nothing if it misses."""
        if not self.first_bank <= bank <= self.last_bank:
            return None
        if self.status <= address <= self.status_end:
            return STATUS
        if self.data <= address <= self.end:
            return DATA
        return None

    @override
    def __repr__(self) -> str:
        return (
            f"<Window ${self.first_bank:02x}-${self.last_bank:02x}:"
            f"{self.data:04x} data, {self.status:04x} status>"
        )


WINDOWS = {
    "dsp": {
        "lorom": Window(0x30, 0x3F, 0x8000, 0xC000, 0xFFFF),
        "hirom": Window(0x00, 0x0F, 0x6000, 0x7000, 0x7FFF),
    },
    "st": {
        "lorom": Window(0x60, 0x67, 0x0000, 0x0001, 0x0001),
        "lorom-shared": Window(0x68, 0x6F, 0x0000, 0x0020, 0x0FFF, 0x0021),
    },
}
"""The parts a window is known for, by the layout the cartridge declares."""


def window_for(part: str, layout: str) -> Window | None:
    """Where that part answers under that layout, or nothing if it does not."""
    if part not in WINDOWS:
        raise UnknownPart(
            f"{part} is not a part with a known window; there are {', '.join(sorted(WINDOWS))}"
        )
    return WINDOWS[part].get(layout)


def busiest(layout: str, reaches: Iterable[tuple[int, int]]) -> str | None:
    """Which part a run of accesses is talking to, by how often each is reached."""
    tally = {}
    for part, layouts in WINDOWS.items():
        window = layouts.get(layout)
        if window is None:
            continue
        hits = sum(1 for bank, address in reaches if window.reaches(bank, address))
        if hits:
            tally[part] = hits
    if not tally:
        return None
    return max(tally, key=lambda part: tally[part])
