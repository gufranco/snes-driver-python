from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Mapping

    from snesdriver.walk import Flags

import collections

from snesdriver import sweep, walk, windows

WRITE = "write"

READ = "read"

POLL = "poll"

UNKNOWN = "?"

RAN = "*"

TRACED = "~"

LONG_STORE = 0x8F
LONG_LOAD = 0xAF
LONG_BYTES = 4


class Step:
    __slots__ = ("address", "bank", "banked", "ran", "traced", "what", "width")

    def __init__(
        self,
        what: str,
        width: int | None,
        address: int,
        bank: int,
        banked: bool = True,
        ran: bool = False,
        traced: bool = False,
    ) -> None:
        self.what = what
        self.width = width
        self.address = address
        self.bank = bank
        self.banked = banked
        self.ran = ran
        self.traced = traced

    @property
    def token(self) -> str:
        marks = (RAN if self.ran else "") + (TRACED if self.traced else "")
        return f"{self.what}{self.width or UNKNOWN}{marks}"

    @property
    def whole(self) -> int:
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
        return sum(step.width or 0 for step in self.steps if step.what == WRITE)

    @property
    def read(self) -> int:
        return sum(step.width or 0 for step in self.steps if step.what == READ)

    @property
    def polls(self) -> int:
        return any(step.what == POLL for step in self.steps)

    @property
    def shape(self) -> str:
        return " ".join(step.token for step in self.steps)

    @property
    def banked(self) -> bool:
        return all(step.banked for step in self.steps)

    def __bool__(self) -> bool:
        return bool(self.steps)

    @override
    def __repr__(self) -> str:
        return f"<Conversation {self.shape or 'nothing'}>"


def seen_by_trace(step: walk.Step, traced: Mapping[int, int] | None) -> int | None:
    if traced is None or step.width is not None:
        return None
    return traced.get(step.offset)


def heard_in(
    walked: Iterable[walk.Step], window: Reaching, traced: Mapping[int, int] | None
) -> Conversation:
    steps = []
    covered = []
    for step in walked:
        if step.depth == 0:
            covered.append(step.offset)
        bank, address = step.bank, step.address
        if bank is None or address is None:
            continue
        register = window.reaches(bank, address)
        if register is None:
            continue
        reading_status = step.reading and register == windows.STATUS
        what = POLL if reading_status else (READ if step.reading else WRITE)
        seen = seen_by_trace(step, traced)
        width = step.width if seen is None else seen
        steps.append(Step(what, width, address, bank, step.banked, step.ran, seen is not None))
    return Conversation(steps, covered)


def at(
    rom: bytes,
    offset: int,
    window: Reaching,
    narrow: bool | None = None,
    limit: int = walk.DEFAULT_LIMIT,
    index: bool | None = None,
    known: Mapping[int, frozenset[Flags]] | None = None,
    ran: bool = False,
    traced: Mapping[int, int] | None = None,
) -> Conversation:
    walked = walk.through(
        rom, offset, narrow=narrow, limit=limit, index=index, known=known, ran=ran
    )
    return heard_in(walked, window, traced)


class Arms:
    __slots__ = ("conversations", "forks", "overflow")

    def __init__(
        self, conversations: Iterable[Conversation], overflow: int, forks: int = 0
    ) -> None:
        self.conversations = tuple(conversations)
        self.overflow = overflow
        self.forks = forks

    @property
    def covered(self) -> frozenset[int]:
        return frozenset().union(*(one.covered for one in self.conversations))


def every(
    rom: bytes,
    offset: int,
    window: Reaching,
    narrow: bool | None = None,
    limit: int = walk.DEFAULT_LIMIT,
    index: bool | None = None,
    known: Mapping[int, frozenset[Flags]] | None = None,
    ran: bool = False,
    traced: Mapping[int, int] | None = None,
    forks: int = walk.DEFAULT_FORKS,
) -> Arms:
    forked = walk.arms(
        rom,
        offset,
        narrow=narrow,
        limit=limit,
        index=index,
        known=known,
        ran=ran,
        forks=forks,
        relevant=lambda step: reaching(step, window),
    )
    return Arms(
        (heard_in(path, window, traced) for path in forked.paths), forked.overflow, forked.forks
    )


def reaching(step: walk.Step, window: Reaching) -> bool:
    bank, address = step.bank, step.address
    return bank is not None and address is not None and window.reaches(bank, address) is not None


class Finding(Protocol):
    def __call__(self, rom: bytes, window: Reaching) -> tuple[int, ...]: ...


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
        for step in sweep.everywhere(rom, entry, kind=kind)
        if step.bank is not None
        and step.address is not None
        and window.reaches(step.bank, step.address)
    }
    return tuple(sorted(found))


Start = tuple["Flags", bool]


def starts(
    offset: int,
    narrow: bool | None,
    known: Mapping[int, frozenset[Flags]],
    ran: Mapping[int, frozenset[Flags]],
) -> list[Start]:
    held = known.get(offset, frozenset({walk.UNKNOWN}))
    found = [(state, False) for state in held if state[0] is not None]
    open_ones = [state for state in held if state[0] is None]
    if not open_ones:
        return found
    settled = ran.get(offset, frozenset())
    if settled:
        return [*found, *((state, True) for state in settled)]
    return [*found, *(((narrow, state[1]), False) for state in open_ones)]


class Heard:
    __slots__ = ("overflow", "shapes", "walks")

    def __init__(self, shapes: dict[str, int], overflow: int, walks: int) -> None:
        self.shapes = shapes
        self.overflow = overflow
        self.walks = walks


def heard(
    rom: bytes,
    window: Reaching,
    narrow: bool | None = None,
    limit: int = walk.DEFAULT_LIMIT,
    find: Finding = sites,
    kind: str | None = None,
    ran: Mapping[int, frozenset[Flags]] | None = None,
    traced: Mapping[int, int] | None = None,
    forks: int = walk.DEFAULT_FORKS,
) -> Heard:
    known = sweep.contexts(rom, kind) if kind is not None else {}
    counted: collections.Counter[str] = collections.Counter()
    seen: set[int] = set()
    spilled = 0
    walks = 0
    for offset in find(rom, window):
        if offset in seen:
            continue
        told_here: set[str] = set()
        for (wide, index), told in starts(offset, narrow, known, ran or {}):
            found = every(rom, offset, window, wide, limit, index, known, told, traced, forks)
            seen |= found.covered
            spilled += found.overflow
            walks += 1
            told_here |= {one.shape for one in found.conversations if one}
        counted.update(told_here)
    return Heard(dict(counted), spilled, walks)


def shapes(
    rom: bytes,
    window: Reaching,
    narrow: bool | None = None,
    limit: int = walk.DEFAULT_LIMIT,
    find: Finding = sites,
    kind: str | None = None,
    ran: Mapping[int, frozenset[Flags]] | None = None,
    traced: Mapping[int, int] | None = None,
    forks: int = walk.DEFAULT_FORKS,
) -> dict[str, int]:
    return heard(rom, window, narrow, limit, find, kind, ran, traced, forks).shapes
