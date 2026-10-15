from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, override, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

import collections

from snesdriver import walk, windows

WRITE = "write"

READ = "read"

POLL = "poll"

LONG_STORE = 0x8F
LONG_LOAD = 0xAF
LONG_BYTES = 4


class Step:
    __slots__ = ("address", "bank", "banked", "what", "width")

    def __init__(
        self,
        what: str,
        width: int,
        address: int | None,
        bank: int | None = None,
        banked: bool = True,
    ) -> None:
        self.what = what
        self.width = width
        self.address = address
        self.bank = bank
        self.banked = banked

    @property
    def whole(self) -> int | None:
        if self.bank is None or self.address is None:
            return None
        return self.bank << 16 | self.address

    @override
    def __repr__(self) -> str:
        return f"<{self.what} {self.width}>"


class Conversation:
    __slots__ = ("covered", "steps")

    def __init__(self, steps: Iterable[Step], covered: Iterable[int] = ()) -> None:
        self.steps = tuple(steps)
        self.covered = frozenset(covered)

    @property
    def written(self) -> int:
        return sum(step.width for step in self.steps if step.what == WRITE)

    @property
    def read(self) -> int:
        return sum(step.width for step in self.steps if step.what == READ)

    @property
    def polls(self) -> int:
        return any(step.what == POLL for step in self.steps)

    @property
    def shape(self) -> str:
        return " ".join(f"{step.what}{step.width}" for step in self.steps)

    @property
    def banked(self) -> bool:
        return all(step.banked for step in self.steps)

    def __bool__(self) -> bool:
        return bool(self.steps)

    @override
    def __repr__(self) -> str:
        return f"<Conversation {self.shape or 'nothing'}>"


def _reached(step: walk.Step, window: Reaching) -> str | None:
    if step.bank is None or step.address is None:
        return None
    return window.reaches(step.bank, step.address)


def at(
    rom: bytes,
    offset: int,
    window: Reaching,
    narrow: bool = True,
    limit: int = walk.DEFAULT_LIMIT,
) -> Conversation:
    steps = []
    covered = []
    for step in walk.through(rom, offset, narrow=narrow, limit=limit):
        if step.depth == 0:
            covered.append(step.offset)
        register = _reached(step, window)
        if register is None:
            continue
        reading_status = step.reading and register == windows.STATUS
        what = POLL if reading_status else (READ if step.reading else WRITE)
        steps.append(Step(what, step.width, step.address, step.bank, step.banked))
    return Conversation(steps, covered)


class Finding(Protocol):
    def __call__(self, rom: bytes, window: Reaching) -> tuple[int, ...]: ...


@runtime_checkable
class Reaching(Protocol):
    def reaches(self, bank: int, address: int) -> str | None: ...


def sites(rom: bytes, window: Reaching) -> tuple[int, ...]:
    found = []
    for at_offset in range(len(rom) - LONG_BYTES + 1):
        if rom[at_offset] not in (LONG_STORE, LONG_LOAD):
            continue
        address = rom[at_offset + 1] | rom[at_offset + 2] << 8
        bank = rom[at_offset + 3]
        if window.reaches(bank, address):
            found.append(at_offset)
    return tuple(found)


def reached(
    rom: bytes,
    window: Reaching,
    entry: int | None = None,
    kind: str = walk.DEFAULT_LAYOUT,
) -> tuple[int, ...]:
    found = {
        step.offset
        for step in walk.everywhere(rom, entry, kind=kind)
        if step.bank is not None
        and step.address is not None
        and window.reaches(step.bank, step.address)
    }
    return tuple(sorted(found))


def shapes(
    rom: bytes,
    window: Reaching,
    narrow: bool = True,
    limit: int = walk.DEFAULT_LIMIT,
    find: Finding = sites,
) -> dict[str, int]:
    counted: collections.Counter[str] = collections.Counter()
    seen: set[int] = set()
    for offset in find(rom, window):
        if offset in seen:
            continue
        found = at(rom, offset, window, narrow=narrow, limit=limit)
        seen |= found.covered
        if found:
            counted[found.shape] += 1
    return dict(counted)
