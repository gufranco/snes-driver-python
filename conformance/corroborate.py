from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT / "mos65xx-python"))
sys.path.append(str(ROOT / "snes-mapper-python"))

from mapper import layout
from mos65xx import disassemble

ACCUMULATOR_FLAG = 0x20

INDEX_FLAG = 0x10

BANK = 0x8000

READ_MODIFY_WRITE = frozenset({"tsb", "trb", "inc", "dec", "asl", "lsr", "rol", "ror"})

STORES = frozenset({"sta", "stz", "stx", "sty"})

SIZED_BY_INDEX = frozenset({"ldx", "ldy", "stx", "sty", "cpx", "cpy"})

SIZED_BY_ACCUMULATOR = frozenset(
    {"lda", "sta", "ora", "and", "eor", "adc", "sbc", "cmp", "bit", "stz"} | READ_MODIFY_WRITE
)

ACCESSING = SIZED_BY_ACCUMULATOR | SIZED_BY_INDEX

INSTRUCTION_SIZES = (2, 3, 4)

NOT_MEMORY = frozenset({"immediate", "immediateA", "immediateX", "implied"})

ONE = "one"

BOTH = "both"

HIGH = "high"

WRITE = "write"

ADDRESS_BITS = 0xFFFFFF

WORD = 0xFFFF

BYTE = 0xFF

NOTHING_FITS = "no instruction ending at the recorded PC reaches the address"

TWO_FIT = "more than one instruction ending at the recorded PC fits"

OUTSIDE = "the instruction ran outside the image"


class Access:
    __slots__ = (
        "address",
        "count",
        "data_bank",
        "direct",
        "direction",
        "emulation",
        "first",
        "pc",
        "status",
        "width",
        "x",
        "y",
    )

    def __init__(self, fields: list[str]) -> None:
        self.direction = fields[0]
        self.address = int(fields[1], 16)
        self.width = int(fields[2])
        self.pc = int(fields[3], 16)
        self.status = int(fields[4], 16)
        self.emulation = fields[5] == "1"
        self.data_bank = int(fields[6], 16)
        self.direct = int(fields[7], 16)
        self.x = int(fields[8], 16)
        self.y = int(fields[9], 16)
        self.count = int(fields[10])
        self.first = int(fields[11])

    @property
    def narrow(self) -> bool:
        return self.emulation or bool(self.status & ACCUMULATOR_FLAG)

    @property
    def narrow_index(self) -> bool:
        return self.emulation or bool(self.status & INDEX_FLAG)


class Decoded:
    __slots__ = ("checked", "expected", "high", "mnemonic", "mode", "offset", "start")

    def __init__(self, one: Any, start: int, expected: int, where: int | None, access: Any) -> None:
        self.offset: int = one.offset
        self.mnemonic: str = one.mnemonic
        self.mode: str = one.mode
        self.start = start
        self.expected = expected
        self.checked = where is not None
        self.high = where is not None and where != access.address


class Verdict:
    __slots__ = ("access", "decoded", "reason")

    def __init__(self, access: Access, decoded: Decoded | None, reason: str | None) -> None:
        self.access = access
        self.decoded = decoded
        self.reason = reason

    @property
    def agrees(self) -> bool:
        return self.reason is None

    @property
    def half(self) -> str:
        if self.decoded is not None and self.decoded.high:
            return HIGH
        return BOTH if self.access.width == 2 else ONE

    @property
    def width(self) -> int:
        return 2 if self.half == HIGH else self.access.width


def offset_of(kind: str, address: int, banks: int) -> int | None:
    found = layout.resolve(kind, address, banks=banks)
    if not found.is_rom or found.offset is None or found.offset >= banks * BANK:
        return None
    at: int = found.offset
    return at


def index_of(access: Access, register: int) -> int:
    return register & BYTE if access.narrow_index else register


def effective(one: Any, access: Access) -> int | None:
    operand: int = one.operand
    banked = (access.data_bank << 16) | operand
    page = access.direct + operand
    where = {
        "absolute": banked,
        "absoluteX": banked + index_of(access, access.x),
        "absoluteY": banked + index_of(access, access.y),
        "absoluteLong": operand,
        "absoluteLongX": operand + index_of(access, access.x),
        "direct": page & WORD,
        "directX": (page + index_of(access, access.x)) & WORD,
        "directY": (page + index_of(access, access.y)) & WORD,
    }.get(one.mode)
    return None if where is None else where & ADDRESS_BITS


def expected_width(mnemonic: str, access: Access) -> int:
    narrow = access.narrow_index if mnemonic in SIZED_BY_INDEX else access.narrow
    return 1 if narrow else 2


def fits(mnemonic: str, direction: str) -> bool:
    if mnemonic in READ_MODIFY_WRITE:
        return True
    return (direction == WRITE) == (mnemonic in STORES)


def decoded_at(rom: bytes, kind: str, start: int, access: Access) -> Any:
    offset = offset_of(kind, start, max(len(rom) // BANK, 1))
    if offset is None:
        return None
    found = disassemble(rom, offset, start, count=1, m=access.narrow, x=access.narrow_index)
    return next(iter(found), None)


def candidates(rom: bytes, kind: str, access: Access) -> Iterator[Decoded]:
    bank, low = access.pc >> 16, access.pc & WORD
    for size in INSTRUCTION_SIZES:
        start = (bank << 16) | ((low - size) & WORD)
        one = decoded_at(rom, kind, start, access)
        if one is None or one.size != size or not accessing(one, access.direction):
            continue
        expected = expected_width(one.mnemonic, access)
        where = effective(one, access)
        if where is not None and where not in landings(access, expected):
            continue
        yield Decoded(one, start, expected, where, access)


def accessing(one: Any, direction: str) -> bool:
    if one.mnemonic not in ACCESSING or one.mode in NOT_MEMORY:
        return False
    return fits(one.mnemonic, direction)


def landings(access: Access, expected: int) -> tuple[int, ...]:
    if access.width == 1 and expected == 2:
        return (access.address, (access.address - 1) & ADDRESS_BITS)
    return (access.address,)


def chosen(found: list[Decoded]) -> list[Decoded]:
    checked = [one for one in found if one.checked]
    return checked or found


def in_image(rom: bytes, kind: str, access: Access) -> bool:
    banks = max(len(rom) // BANK, 1)
    return offset_of(kind, access.pc, banks) is not None


def corroborated(rom: bytes, kind: str, access: Access) -> Verdict:
    if not in_image(rom, kind, access):
        return Verdict(access, None, OUTSIDE)
    found = chosen(list(candidates(rom, kind, access)))
    if not found:
        return Verdict(access, None, NOTHING_FITS)
    if len(found) > 1:
        return Verdict(access, None, TWO_FIT)
    one = found[0]
    if one.expected != (2 if one.high else access.width):
        return Verdict(
            access,
            one,
            f"the bus moved {access.width} bytes and {one.mnemonic} under the recorded flags"
            f" moves {one.expected}",
        )
    return Verdict(access, one, None)
