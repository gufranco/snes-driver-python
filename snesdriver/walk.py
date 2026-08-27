"""Reading a cartridge routine one instruction at a time.

A cartridge talks to its coprocessor with ordinary 65816 code, so the shape of
the conversation is visible in the code itself: which addresses it touches, in
what order, and how wide each access was. Nothing here executes anything. It
walks straight through a routine from its first instruction to the first one that
leaves, and reports what each instruction reached.

Width is the part that cannot be skipped. A store to a coprocessor moves one byte
or two depending on the accumulator, and the accumulator's width is not in the
instruction: it was set earlier by a `sep` or a `rep`. A walk that ignores those
reads every access at the wrong size and reports a conversation the console never
had, so the width is carried along and reported with each access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "mos65xx-python"))

from mos65xx import disassemble

ACCUMULATOR = 0x20
"""The bit `sep` and `rep` use to name the accumulator."""

LEAVING = ("rts", "rtl", "rti", "jmp", "jml", "jsr", "jsl", "bra", "brl", "stp")
"""Instructions after which the straight walk has nothing left to read."""

IMMEDIATE = ("immediate", "immediateA", "immediateX")

BRANCHES = ("relative", "relativeLong")

BACKWARDS = 0x80

DEFAULT_LIMIT = 80


LONG = "absoluteLong"

ABSOLUTE = "absolute"

REACHING = (LONG, ABSOLUTE)
"""The two modes that can name a coprocessor register.

An indexed mode could reach one too, and is left out: the index is in a register
this does not track, so the address an indexed access lands on is not something
that can be read off the instruction. A mode nobody can resolve is worse here
than a mode nobody reads, because the first reports a place the console never
touched.
"""


class Step:
    """One instruction, and what it reached."""

    __slots__ = ("in_bank", "mnemonic", "narrow", "offset", "one", "width")

    def __init__(self, one: Any, narrow: bool, in_bank: int = 0) -> None:
        self.one = one
        self.narrow = narrow
        self.in_bank = in_bank
        self.offset = one.offset
        self.mnemonic = one.mnemonic
        self.width = 1 if narrow else 2

    @property
    def banked(self) -> bool:
        """Whether the instruction carried the bank it reached.

        A long load or store spells all three bytes, so the bank is read rather
        than worked out. An ordinary absolute one spells two, and takes its bank
        from the data bank register, which nothing here tracks. Everything that
        reports a bank has to say which of the two it had, because a shape that
        mixes them silently claims more than it knows.
        """
        found = self.one.mode == LONG
        assert isinstance(found, bool)
        return found

    @property
    def bank(self) -> int | None:
        """The bank it reached, or nothing if it reached none.

        For an absolute access this is the bank the routine itself is executing
        in, which is the assumption and not a reading. It is right whenever the
        data bank register still holds the program bank, which is what the code
        that reaches a part in its own bank usually arranges, and it is wrong
        without warning otherwise. `banked` is how a caller tells the two apart.
        """
        if self.one.mode == LONG:
            found = (self.one.operand >> 16) & 0xFF
            assert isinstance(found, int)
            return found
        if self.one.mode == ABSOLUTE:
            return self.in_bank
        return None

    @property
    def address(self) -> int | None:
        """The address inside that bank."""
        if self.one.mode not in REACHING:
            return None
        found = self.one.operand & 0xFFFF
        assert isinstance(found, int)
        return found

    @property
    def reading(self) -> bool:
        """Whether the access took a value from the part rather than giving one."""
        return not self.mnemonic.startswith("st")

    @property
    def immediate(self) -> int | None:
        """The constant the instruction carries, or nothing if it carries none."""
        if self.one.mode not in IMMEDIATE:
            return None
        found = self.one.operand
        assert isinstance(found, int)
        return found

    @property
    def waiting(self) -> bool:
        """Whether the instruction branches backwards, which is how a routine waits."""
        return self.one.mode in BRANCHES and bool(self.one.operand & BACKWARDS)

    @override
    def __repr__(self) -> str:
        return f"<Step {self.one.text} {'byte' if self.narrow else 'word'}>"


def through(
    rom: bytes,
    offset: int,
    narrow: bool = True,
    limit: int = DEFAULT_LIMIT,
    address: int | None = None,
    bank: int | None = None,
) -> Iterator[Step]:
    """Walk a routine from an offset, yielding one step per instruction read.

    The bank the routine runs in defaults to the one a low cartridge puts that
    offset in, which is the same rule this already uses to work out the address.
    It matters only for an absolute access, where it stands in for a data bank
    register nothing here tracks; see `Step.banked`.
    """
    at = address if address is not None else 0x8000 + offset % 0x8000
    in_bank = bank if bank is not None else offset // 0x8000
    for _ in range(limit):
        read = disassemble(rom, offset, at, count=1, m=narrow, x=True)
        if not read:
            return
        one = read[0]
        yield Step(one, narrow, in_bank)
        if one.mnemonic in ("sep", "rep") and one.operand & ACCUMULATOR:
            narrow = one.mnemonic == "sep"
        if one.mnemonic in LEAVING:
            return
        offset += one.size
        at += one.size
