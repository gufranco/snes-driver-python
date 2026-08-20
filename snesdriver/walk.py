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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mos65xx-python"))

from mos65xx import disassemble

ACCUMULATOR = 0x20
"""The bit `sep` and `rep` use to name the accumulator."""

LEAVING = ("rts", "rtl", "rti", "jmp", "jml", "jsr", "jsl", "bra", "brl", "stp")
"""Instructions after which the straight walk has nothing left to read."""

IMMEDIATE = ("immediate", "immediateA", "immediateX")

BRANCHES = ("relative", "relativeLong")

BACKWARDS = 0x80

DEFAULT_LIMIT = 80


class Step:
    """One instruction, and what it reached."""

    def __init__(self, one, narrow):
        self.one = one
        self.narrow = narrow
        self.offset = one.offset
        self.mnemonic = one.mnemonic
        self.width = 1 if narrow else 2

    @property
    def bank(self):
        """The bank of the long address it reached, or nothing if it reached none."""
        if self.one.mode != "absoluteLong":
            return None
        return (self.one.operand >> 16) & 0xFF

    @property
    def address(self):
        """The address inside that bank."""
        if self.one.mode != "absoluteLong":
            return None
        return self.one.operand & 0xFFFF

    @property
    def reading(self):
        """Whether the access took a value from the part rather than giving one."""
        return not self.mnemonic.startswith("st")

    @property
    def immediate(self):
        """The constant the instruction carries, or nothing if it carries none."""
        if self.one.mode not in IMMEDIATE:
            return None
        return self.one.operand

    @property
    def waiting(self):
        """Whether the instruction branches backwards, which is how a routine waits."""
        return self.one.mode in BRANCHES and bool(self.one.operand & BACKWARDS)

    def __repr__(self):
        return f"<Step {self.one.text} {'byte' if self.narrow else 'word'}>"


def through(rom, offset, narrow=True, limit=DEFAULT_LIMIT, address=None):
    """Walk a routine from an offset, yielding one step per instruction read."""
    at = address if address is not None else 0x8000 + offset % 0x8000
    for _ in range(limit):
        read = disassemble(rom, offset, at, count=1, m=narrow, x=True)
        if not read:
            return
        one = read[0]
        yield Step(one, narrow)
        if one.mnemonic in ("sep", "rep") and one.operand & ACCUMULATOR:
            narrow = one.mnemonic == "sep"
        if one.mnemonic in LEAVING:
            return
        offset += one.size
        at += one.size
