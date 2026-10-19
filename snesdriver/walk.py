from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator, Mapping

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "mos65xx-python"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "snes-mapper-python"))

from mapper import layout
from mos65xx import disassemble

ACCUMULATOR = 0x20

INDEX = 0x10

BANK = 0x8000

LEAVING = ("rts", "rtl", "rti", "jmp", "jml", "bra", "brl", "stp")

IMMEDIATE = ("immediate", "immediateA", "immediateX")

RELATIVE = "relative"

RELATIVE_WORD = "relativeWord"

BRANCHES = (RELATIVE, RELATIVE_WORD)

BACKWARDS = {RELATIVE: 0x80, RELATIVE_WORD: 0x8000}

DEFAULT_LIMIT = 80

DEFAULT_LAYOUT = layout.LOROM


LONG = "absoluteLong"

ABSOLUTE = "absolute"

NOT_MEMORY = ("pea", "per")

REACHING = (LONG, ABSOLUTE)

SIZED_BY_ACCUMULATOR = "immediateA"

SIZED_BY_INDEX = "immediateX"

SETTING = ("sep", "rep")

Width = bool | None

Flags = tuple[Width, Width]

Saved = tuple[Flags, ...]

UNKNOWN: Flags = (None, None)

EMULATION: Flags = (True, True)


class Step:
    __slots__ = ("depth", "in_bank", "mnemonic", "narrow", "offset", "one", "ran", "width")

    def __init__(
        self, one: Any, narrow: Width, in_bank: int = 0, depth: int = 0, ran: bool = False
    ) -> None:
        self.one = one
        self.narrow = narrow
        self.in_bank = in_bank
        self.depth = depth
        self.ran = ran
        self.offset = one.offset
        self.mnemonic = one.mnemonic
        self.width: int | None = None if narrow is None else (1 if narrow else 2)

    @property
    def banked(self) -> bool:
        found = self.one.mode == LONG
        assert isinstance(found, bool)
        return found

    @property
    def bank(self) -> int | None:
        if self.one.mode == LONG:
            found = (self.one.operand >> 16) & 0xFF
            assert isinstance(found, int)
            return found
        if self.one.mode == ABSOLUTE and self.mnemonic not in NOT_MEMORY:
            return self.in_bank
        return None

    @property
    def address(self) -> int | None:
        if self.one.mode not in REACHING or self.mnemonic in NOT_MEMORY:
            return None
        found = self.one.operand & 0xFFFF
        assert isinstance(found, int)
        return found

    @property
    def reading(self) -> bool:
        return not self.mnemonic.startswith("st")

    @property
    def immediate(self) -> int | None:
        if self.one.mode not in IMMEDIATE:
            return None
        found = self.one.operand
        assert isinstance(found, int)
        return found

    @property
    def waiting(self) -> bool:
        if self.one.mode not in BRANCHES:
            return False
        return bool(self.one.operand & BACKWARDS[self.one.mode])

    @override
    def __repr__(self) -> str:
        size = "unknown" if self.narrow is None else ("byte" if self.narrow else "word")
        return f"<Step {self.one.text} {size}>"


def _set(one: Any, state: Flags) -> Flags:
    to = one.mnemonic == "sep"
    narrow, index = state
    return (
        to if one.operand & ACCUMULATOR else narrow,
        to if one.operand & INDEX else index,
    )


def flags(one: Any, state: Flags, saved: Saved) -> tuple[Flags, Saved]:
    if one.mnemonic in SETTING and one.operand is not None:
        return _set(one, state), saved
    if one.mnemonic == "php":
        return state, (*saved, state)
    if one.mnemonic == "plp":
        return (saved[-1], saved[:-1]) if saved else (UNKNOWN, saved)
    return state, saved


def sets_width(one: Any) -> bool:
    if one.mnemonic == "plp":
        return True
    return one.mnemonic in SETTING and one.operand is not None and bool(one.operand & ACCUMULATOR)


def unplaceable(one: Any, state: Flags) -> bool:
    return (state[0] is None and one.mode == SIZED_BY_ACCUMULATOR) or (
        state[1] is None and one.mode == SIZED_BY_INDEX
    )


def decoded(rom: bytes, offset: int, address: int, state: Flags) -> Any:
    read = disassemble(
        rom, offset, address, count=1, m=state[0] is not False, x=state[1] is not False
    )
    return read[0] if read else None


def resumed(known: Mapping[int, frozenset[Flags]] | None, offset: int) -> Flags:
    held = known.get(offset, frozenset()) if known is not None else frozenset()
    return next(iter(held)) if len(held) == 1 else UNKNOWN


CALLS = ("jsr", "jsl")

JUMPS = ("jmp", "jml", "bra", "brl")

DIRECT = ("absolutePC", LONG)


def offset_of(bank: int, address: int, banks: int, kind: str = DEFAULT_LAYOUT) -> int | None:
    found = layout.resolve(kind, (bank << 16) | address, banks=banks)
    if not found.is_rom or found.offset is None or found.offset >= banks * BANK:
        return None
    at = found.offset
    assert isinstance(at, int)
    return at


def target_of(one: Any, bank: int) -> tuple[int, int] | None:
    if one.operand is None:
        return None
    if one.mode in BRANCHES:
        sign = BACKWARDS[one.mode]
        away = one.operand - 2 * sign if one.operand & sign else one.operand
        return bank, (one.address + one.size + away) & 0xFFFF
    if one.mnemonic in CALLS or one.mnemonic in JUMPS:
        if one.mode not in DIRECT:
            return None
        into = (one.operand >> 16) & 0xFF if one.mode == LONG else bank
        return into, one.operand & 0xFFFF
    return None


RETURNING = ("rts", "rtl")

DESCENT_ROOM = 16

DEFAULT_DEPTH = 8


class Frame:
    __slots__ = ("address", "bank", "offset")

    def __init__(self, offset: int, address: int, bank: int) -> None:
        self.offset = offset
        self.address = address
        self.bank = bank


class Walker:
    __slots__ = ("at", "banks", "in_bank", "known", "offset", "rom", "saved", "stack", "state")

    def __init__(
        self,
        rom: bytes,
        offset: int,
        at: int,
        in_bank: int,
        state: Flags,
        known: Mapping[int, frozenset[Flags]] | None,
    ) -> None:
        self.rom = rom
        self.offset = offset
        self.at = at
        self.in_bank = in_bank
        self.state = state
        self.known = known
        self.banks = max(len(rom) // BANK, 1)
        self.stack: list[Frame] = []
        self.saved: Saved = ()

    def descend(self, one: Any, depth: int) -> bool:
        if one.mnemonic not in CALLS:
            return False
        called = (
            _called(one, self.in_bank, self.banks, self.rom, self.state)
            if len(self.stack) < depth
            else None
        )
        if called is None:
            self.state = resumed(self.known, self.offset + one.size)
            return False
        self.stack.append(Frame(self.offset + one.size, self.at + one.size, self.in_bank))
        self.in_bank, self.at = called
        self.offset = offset_of(self.in_bank, self.at, self.banks) or 0
        return True

    def leave(self, one: Any) -> bool:
        if one.mnemonic in RETURNING and self.stack:
            back = self.stack.pop()
            self.offset, self.at, self.in_bank = back.offset, back.address, back.bank
            return False
        if one.mnemonic in LEAVING:
            landing = _inside_a_helper(one, self.in_bank, self.banks) if self.stack else None
            if landing is None:
                return True
            self.offset, self.in_bank, self.at = landing
            return False
        self.offset += one.size
        self.at += one.size
        return False


def through(
    rom: bytes,
    offset: int,
    narrow: Width = None,
    limit: int = DEFAULT_LIMIT,
    address: int | None = None,
    bank: int | None = None,
    depth: int = DEFAULT_DEPTH,
    index: Width = None,
    known: Mapping[int, frozenset[Flags]] | None = None,
    ran: bool = False,
) -> Iterator[Step]:
    at = address if address is not None else BANK + offset % BANK
    in_bank = bank if bank is not None else offset // BANK
    walker = Walker(rom, offset, at, in_bank, (narrow, index), known)
    spent = 0
    total = 0
    while spent < limit and total < limit * DESCENT_ROOM:
        total += 1
        one = decoded(rom, walker.offset, walker.at, walker.state)
        if one is None:
            return
        spent += 1 if not walker.stack else 0
        yield Step(one, walker.state[0], walker.in_bank, len(walker.stack), ran)
        if unplaceable(one, walker.state):
            return
        ran = ran and not sets_width(one)
        walker.state, walker.saved = flags(one, walker.state, walker.saved)
        if walker.descend(one, depth):
            continue
        ran = ran and one.mnemonic not in CALLS
        if walker.leave(one):
            return


def _inside_a_helper(one: Any, bank: int, banks: int) -> tuple[int, int, int] | None:
    if one.mnemonic not in JUMPS:
        return None
    target = target_of(one, bank)
    if target is None:
        return None
    offset = offset_of(*target, banks)
    if offset is None:
        return None
    return offset, *target


PROBE_LIMIT = 200

NOT_CODE = ("brk", "cop", "stp", "wdm")


def _returns(rom: bytes, target: tuple[int, int], state: Flags, banks: int) -> bool:
    bank, at = target
    seen: set[int] = set()
    for _ in range(PROBE_LIMIT):
        offset = offset_of(bank, at, banks)
        if offset is None or offset in seen:
            return False
        seen.add(offset)
        one = decoded(rom, offset, at, state)
        if one is None or unplaceable(one, state):
            return False
        if one.mnemonic in NOT_CODE:
            return False
        if one.mnemonic in RETURNING:
            return True
        if one.mnemonic in LEAVING:
            found = target_of(one, bank)
            if found is None or offset_of(*found, banks) is None:
                return False
            bank, at = found
            continue
        at += one.size
        if at > 0xFFFF:
            return False
    return False


def _called(one: Any, bank: int, banks: int, rom: bytes, state: Flags) -> tuple[int, int] | None:
    target = target_of(one, bank)
    if target is None or offset_of(*target, banks) is None:
        return None
    if not _returns(rom, target, state, banks):
        return None
    return target
