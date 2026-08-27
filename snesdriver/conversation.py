"""What a cartridge routine actually says to a part, read out of its own code.

A coprocessor's protocol is written down in exactly one place: the code the
cartridge runs to drive it. No datasheet survives for most of these parts, and
the emulators that talk to them were written by people who read the same code.
So this reads it too, rather than guessing from the outside.

What comes back is the shape of an exchange: how many bytes go each way, how wide
each access is, and whether the routine waits on the part between them. That is
the piece a model cannot supply and a caller cannot invent, because the part
gives no way to ask. On the DSP-1 the one bit the console can see stays asserted
throughout, so nothing about the exchange can be discovered by watching it.

Nothing here executes anything. It walks straight through a routine and reports
what each instruction reached, which is why a shape is evidence rather than a
guess: it is the cartridge's own sequence, read in the order the console runs it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, override, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

import collections

from snesdriver import walk, windows

WRITE = "write"

READ = "read"

POLL = "poll"
"""A read of a status register, which is the only thing a poll can be.

Every access landing in a status range was a poll until the ST018, whichever way
it went, so a console writing a control register and a console reading it made
the same entry. A write is a write wherever it lands; where it landed is already
in the address beside it.
"""

LONG_STORE = 0x8F
LONG_LOAD = 0xAF
LONG_BYTES = 4


class Step:
    """One access a routine makes to the part.

    The bank is carried alongside the address because a part with more than one
    window is told apart by it: the Seta parts answer at a port in one bank range
    and through shared memory in the next, and an address with the bank dropped
    cannot say which of the two a routine meant.
    """

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
        """Bank and address together, as the instruction carried them."""
        if self.bank is None or self.address is None:
            return None
        return self.bank << 16 | self.address

    @override
    def __repr__(self) -> str:
        return f"<{self.what} {self.width}>"


class Conversation:
    """Everything one routine says to a part, in the order it says it."""

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
        """The exchange as a string, so two routines can be compared by it."""
        return " ".join(f"{step.what}{step.width}" for step in self.steps)

    @property
    def banked(self) -> bool:
        """Whether every access here carried the bank it reached.

        False when any of them was an ordinary absolute access, whose bank was
        the routine's own rather than one the instruction spelled. A caller
        recording a shape has to keep this beside it: the accesses are the same
        either way, and what is known about where they landed is not.
        """
        return all(step.banked for step in self.steps)

    def __bool__(self) -> bool:
        return bool(self.steps)

    @override
    def __repr__(self) -> str:
        return f"<Conversation {self.shape or 'nothing'}>"


def _reached(step: walk.Step, window: Reaching) -> str | None:
    """Which register an instruction touched, or nothing if it touched none."""
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
    """The conversation a routine at that offset has with a part at that window."""
    steps = []
    covered = []
    for step in walk.through(rom, offset, narrow=narrow, limit=limit):
        covered.append(step.offset)
        register = _reached(step, window)
        if register is None:
            continue
        reading_status = step.reading and register == windows.STATUS
        what = POLL if reading_status else (READ if step.reading else WRITE)
        steps.append(Step(what, step.width, step.address, step.bank, step.banked))
    return Conversation(steps, covered)


class Finding(Protocol):
    """How `shapes` locates the instructions that reach a part.

    A protocol rather than a choice of two names, so a caller with a part that
    neither question suits can hand over its own.
    """

    def __call__(self, rom: bytes, window: Reaching) -> tuple[int, ...]:
        """Every offset holding an instruction that reaches that part."""
        ...


@runtime_checkable
class Reaching(Protocol):
    """What `sites` and `at` need a window to be, which is one question.

    Written as a protocol so a caller with a part that answers in more than one
    place can hand over something that covers both, rather than walking the same
    routine once per window and getting two halves of one exchange.
    """

    def reaches(self, bank: int, address: int) -> str | None:
        """Which register an access lands on, or nothing if it misses."""
        ...


def sites(rom: bytes, window: Reaching) -> tuple[int, ...]:
    """Every offset holding an instruction that reaches the part.

    A long load or store carries its whole address in the three bytes after the
    opcode, so the search is exact rather than heuristic: no other encoding puts
    that bank and that address there.
    """
    found = []
    for at_offset in range(len(rom) - LONG_BYTES + 1):
        if rom[at_offset] not in (LONG_STORE, LONG_LOAD):
            continue
        address = rom[at_offset + 1] | rom[at_offset + 2] << 8
        bank = rom[at_offset + 3]
        if window.reaches(bank, address):
            found.append(at_offset)
    return tuple(found)


def reached(rom: bytes, window: Reaching, entry: int | None = None) -> tuple[int, ...]:
    """The same question as `sites`, asked by following control flow instead.

    `sites` searches for the bytes that spell a long access, which is exact and
    sees nothing else. A part reached by an ordinary absolute access needs this
    one: it starts where the console starts and decodes only what control flow
    arrives at, so an access it reports is an instruction rather than two bytes
    of data that happened to spell an address.

    It is the slower question and the less complete one. A computed jump is not
    followed, so this finds routines rather than proving there are no others,
    and a part whose driver is only reached through one will come back empty.
    """
    found = {
        step.offset
        for step in walk.everywhere(rom, entry)
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
    """Every distinct exchange in an image, and how many routines have it.

    A site that an earlier walk already stepped over does not start a
    conversation of its own. Every instruction touching the part is a site, but a
    routine that writes and then reads is one exchange rather than two, and
    walking from its middle would report the tail as though it were the whole.

    `find` is how the sites are located, and it is a parameter because the two
    ways of locating them answer for different parts: `sites` for one reached by
    a long access and `reached` for one reached absolutely.
    """
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
