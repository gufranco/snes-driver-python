from __future__ import annotations

from typing import TYPE_CHECKING, override

from .errors import UnknownPart

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

DATA = "data"

STATUS = "status"

MIRROR = 0x80


class Window:
    __slots__ = ("data", "end", "first_bank", "last_bank", "mirrored", "status", "status_end")

    def __init__(
        self,
        first_bank: int,
        last_bank: int,
        data: int,
        status: int,
        end: int,
        status_end: int | None = None,
        mirrored: bool = False,
    ) -> None:
        self.first_bank = first_bank
        self.last_bank = last_bank
        self.data = data
        self.status = status
        self.end = end
        self.status_end = end if status_end is None else status_end
        self.mirrored = mirrored

    def reaches(self, bank: int, address: int) -> str | None:
        held = bank & (MIRROR - 1) if self.mirrored else bank
        if not self.first_bank <= held <= self.last_bank:
            return None
        if self.status <= address <= self.status_end:
            return STATUS
        if self.data <= address <= self.end:
            return DATA
        return None

    @override
    def __repr__(self) -> str:
        banks = f"${self.first_bank:02x}-${self.last_bank:02x}"
        if self.mirrored:
            banks += f",${self.first_bank | MIRROR:02x}-${self.last_bank | MIRROR:02x}"
        return f"<Window {banks}:{self.data:04x} data, {self.status:04x} status>"


WINDOWS = {
    "dsp": {
        "lorom": Window(0x30, 0x3F, 0x8000, 0xC000, 0xBFFF, 0xFFFF, mirrored=True),
        "hirom": Window(0x00, 0x0F, 0x6000, 0x7000, 0x6FFF, 0x7FFF, mirrored=True),
    },
    "st": {
        "lorom": Window(0x60, 0x67, 0x0000, 0x0001, 0x0001),
        "lorom-shared": Window(0x68, 0x6F, 0x0000, 0x0020, 0x0FFF, 0x0021),
    },
    "obc1": {
        "lorom": Window(0x00, 0x3F, 0x6000, 0x7FF0, 0x7FFF),
    },
    "st018": {
        "lorom": Window(0x00, 0x3F, 0x3800, 0x3804, 0x3803, 0x3804),
    },
}


def window_for(part: str, layout: str) -> Window | None:
    if part not in WINDOWS:
        raise UnknownPart(
            f"{part} is not a part with a known window; there are {', '.join(sorted(WINDOWS))}"
        )
    return WINDOWS[part].get(layout)


def busiest(layout: str, reaches: Iterable[tuple[int, int]]) -> str | None:
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
