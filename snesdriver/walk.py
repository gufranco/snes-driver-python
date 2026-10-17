from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "mos65xx-python"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "snes-mapper-python"))

from mapper import layout
from mos65xx import disassemble

ACCUMULATOR = 0x20

INDEX = 0x10

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


class Step:
    __slots__ = ("depth", "in_bank", "mnemonic", "narrow", "offset", "one", "width")

    def __init__(self, one: Any, narrow: bool, in_bank: int = 0, depth: int = 0) -> None:
        self.one = one
        self.narrow = narrow
        self.in_bank = in_bank
        self.depth = depth
        self.offset = one.offset
        self.mnemonic = one.mnemonic
        self.width = 1 if narrow else 2

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
        return f"<Step {self.one.text} {'byte' if self.narrow else 'word'}>"


CALLS = ("jsr", "jsl")

JUMPS = ("jmp", "jml", "bra", "brl")

DIRECT = ("absolutePC", LONG)

VECTORS = (0xFFE4, 0xFFE6, 0xFFE8, 0xFFEA, 0xFFEE, 0xFFF4, 0xFFF8, 0xFFFA, 0xFFFC, 0xFFFE)

EVERYWHERE_LIMIT = 400000


def everywhere(
    rom: bytes,
    entry: int | None = None,
    limit: int = EVERYWHERE_LIMIT,
    kind: str = DEFAULT_LAYOUT,
) -> Iterator[Step]:
    banks = len(rom) // 0x8000
    pending = [(0x00, one, True, True) for one in _entries(rom, entry, banks, kind)]
    seen: set[tuple[int, int]] = set()
    spent = 0

    while pending and spent < limit:
        bank, address, narrow, index = pending.pop()
        while spent < limit:
            spent += 1
            if (bank, address) in seen:
                break
            seen.add((bank, address))
            offset = _offset(bank, address, banks, kind)
            if offset is None:
                break
            read = disassemble(rom, offset, address, count=1, m=narrow, x=index)
            if not read:
                break
            one = read[0]
            yield Step(one, narrow, bank)

            if one.mnemonic in ("sep", "rep") and one.operand is not None:
                if one.operand & ACCUMULATOR:
                    narrow = one.mnemonic == "sep"
                if one.operand & INDEX:
                    index = one.mnemonic == "sep"

            target = _target(one, bank)
            if target is not None and _offset(*target, banks, kind) is not None:
                if one.mnemonic in JUMPS:
                    bank, address = target
                    continue
                pending.append((*target, narrow, index))

            if one.mnemonic in LEAVING:
                break
            address += one.size
            if address > 0xFFFF:
                break


def _entries(
    rom: bytes, entry: int | None, banks: int, kind: str = DEFAULT_LAYOUT
) -> tuple[int, ...]:
    if entry is not None:
        return (entry,)
    found = []
    for vector in VECTORS:
        at = _offset(0x00, vector, banks, kind)
        if at is None:
            continue
        address = int.from_bytes(rom[at : at + 2], "little")
        if _offset(0x00, address, banks, kind) is not None and address not in found:
            found.append(address)
    return tuple(found)


def _offset(bank: int, address: int, banks: int, kind: str = DEFAULT_LAYOUT) -> int | None:
    found = layout.resolve(kind, (bank << 16) | address, banks=banks)
    if not found.is_rom or found.offset is None or found.offset >= banks * 0x8000:
        return None
    at = found.offset
    assert isinstance(at, int)
    return at


def _target(one: Any, bank: int) -> tuple[int, int] | None:
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


def through(
    rom: bytes,
    offset: int,
    narrow: bool = True,
    limit: int = DEFAULT_LIMIT,
    address: int | None = None,
    bank: int | None = None,
    depth: int = DEFAULT_DEPTH,
) -> Iterator[Step]:
    at = address if address is not None else 0x8000 + offset % 0x8000
    in_bank = bank if bank is not None else offset // 0x8000
    banks = max(len(rom) // 0x8000, 1)
    stack: list[Frame] = []
    spent = 0
    total = 0
    while spent < limit and total < limit * DESCENT_ROOM:
        total += 1
        read = disassemble(rom, offset, at, count=1, m=narrow, x=True)
        if not read:
            return
        one = read[0]
        spent += 1 if not stack else 0
        yield Step(one, narrow, in_bank, len(stack))
        if one.mnemonic in ("sep", "rep") and one.operand & ACCUMULATOR:
            narrow = one.mnemonic == "sep"

        called = _called(one, in_bank, banks, rom, narrow) if len(stack) < depth else None
        if called is not None:
            stack.append(Frame(offset + one.size, at + one.size, in_bank))
            in_bank, at = called
            offset = _offset(in_bank, at, banks) or 0
            continue

        if one.mnemonic in RETURNING and stack:
            back = stack.pop()
            offset, at, in_bank = back.offset, back.address, back.bank
            continue
        if one.mnemonic in LEAVING:
            return
        offset += one.size
        at += one.size


PROBE_LIMIT = 200

NOT_CODE = ("brk", "cop", "stp", "wdm")


def _returns(rom: bytes, target: tuple[int, int], narrow: bool, banks: int) -> bool:
    bank, at = target
    seen: set[int] = set()
    for _ in range(PROBE_LIMIT):
        offset = _offset(bank, at, banks)
        if offset is None or offset in seen:
            return False
        seen.add(offset)
        read = disassemble(rom, offset, at, count=1, m=narrow, x=True)
        if not read:
            return False
        one = read[0]
        if one.mnemonic in NOT_CODE:
            return False
        if one.mnemonic in RETURNING:
            return True
        if one.mnemonic in LEAVING:
            found = _target(one, bank)
            if found is None or _offset(*found, banks) is None:
                return False
            bank, at = found
            continue
        at += one.size
        if at > 0xFFFF:
            return False
    return False


def _called(one: Any, bank: int, banks: int, rom: bytes, narrow: bool) -> tuple[int, int] | None:
    if one.mnemonic not in CALLS:
        return None
    target = _target(one, bank)
    if target is None or _offset(*target, banks) is None:
        return None
    if not _returns(rom, target, narrow, banks):
        return None
    return target
