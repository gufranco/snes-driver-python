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

INDEX = 0x10
"""The bit they use to name the index registers, which decide an instruction's
length the same way the accumulator does.
"""

LEAVING = ("rts", "rtl", "rti", "jmp", "jml", "bra", "brl", "stp")
"""Instructions after which the straight walk has nothing left to read.

A call is not one of them. `jsr` and `jsl` were here until the ST018, whose send
routine calls a guard and then makes its access, so stopping at the call reported
that routine as saying nothing at all. A call comes back, and the instruction
after it is the next one the console runs.

A return is only one of them at the top. Inside a callee the walk goes back to
the caller, which is what `Frame` is for. A `jmp` is here because a straight walk
has nowhere to go after one, and the sweep in `everywhere` is what follows those.
"""

IMMEDIATE = ("immediate", "immediateA", "immediateX")

RELATIVE = "relative"

RELATIVE_WORD = "relativeWord"

BRANCHES = (RELATIVE, RELATIVE_WORD)

BACKWARDS = {RELATIVE: 0x80, RELATIVE_WORD: 0x8000}
"""The sign bit of a displacement, which is not the same bit in both branches.

A short branch carries one byte and a `brl` carries two, so a single mask reads
the wrong bit for one of them. This said `relativeLong` and `0x80` until a
synthetic image was walked past a `brl`: no instruction uses that mode name, so
the long branch matched nothing and every one of them read as forwards.
"""

DEFAULT_LIMIT = 80


LONG = "absoluteLong"

ABSOLUTE = "absolute"

NOT_MEMORY = ("pea", "per")
"""Instructions that carry an address and never touch memory at it.

`pea` pushes the constant it names and `per` pushes an address it computes, and
the disassembler gives both the same `absolute` mode a load or a store has. Until
absolute accesses were read at all this cost nothing, because no part was reached
absolutely. It costs a false access now: the ST018 answers in banks `$00` to
`$3F`, so a `pea $3800` anywhere in that range would be recorded as a write to
its data port, and the routine that pushed a constant would be reported as a
routine that spoke to the part.
"""

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

    __slots__ = ("depth", "in_bank", "mnemonic", "narrow", "offset", "one", "width")

    def __init__(self, one: Any, narrow: bool, in_bank: int = 0, depth: int = 0) -> None:
        self.one = one
        self.narrow = narrow
        self.in_bank = in_bank
        self.depth = depth
        """How many calls deep this instruction is from where the walk started.

        A caller counting routines needs it. A walk that steps into a callee
        reads instructions belonging to a routine somebody else also calls, so
        treating those offsets as covered would let one walk absorb every other
        routine that shares a helper. Zero is the routine that was asked for.
        """
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
        if self.one.mode == ABSOLUTE and self.mnemonic not in NOT_MEMORY:
            return self.in_bank
        return None

    @property
    def address(self) -> int | None:
        """The address inside that bank."""
        if self.one.mode not in REACHING or self.mnemonic in NOT_MEMORY:
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
        if self.one.mode not in BRANCHES:
            return False
        return bool(self.one.operand & BACKWARDS[self.one.mode])

    @override
    def __repr__(self) -> str:
        return f"<Step {self.one.text} {'byte' if self.narrow else 'word'}>"


CALLS = ("jsr", "jsl")

JUMPS = ("jmp", "jml", "bra", "brl")

DIRECT = ("absolutePC", LONG)
"""The modes a jump or a call spells its destination in.

`jmp` also has three indirect modes, which name a place to read the destination
from rather than the destination. Following one would report control arriving
somewhere the console never went, so they are left alone and the sweep stops
there instead.
"""

RESET_VECTOR = 0x7FFC

VECTORS = (0x7FE4, 0x7FE6, 0x7FE8, 0x7FEA, 0x7FEE, 0x7FF4, 0x7FF8, 0x7FFA, 0x7FFC, 0x7FFE)
"""Every vector a low cartridge publishes, native and emulation.

Reset is one of twelve and it is not where most driver code is reached from. A
console spends its life in an interrupt handler, so a sweep seeded only from
reset misses whatever the handlers call. Metal Combat is the case that showed
it: from reset alone the sweep decoded 1,675 instructions and reached the OBC1
not once, while a search of the same image for the bytes that spell a long
access found 129 sites.

The two unused slots at `0x7FEC` and `0x7FF6` are left out. They hold whatever
the assembler put there, which is as likely to be a byte of the title as an
address.
"""

EVERYWHERE_LIMIT = 400000
"""Instructions one sweep of an image will decode before giving up.

A backstop rather than a budget: a sweep that reaches it has found a loop this
does not understand, and the count is far above what any image on hand needs.
The largest cartridge read here settles in under two thousand.
"""


def everywhere(
    rom: bytes,
    entry: int | None = None,
    limit: int = EVERYWHERE_LIMIT,
) -> Iterator[Step]:
    """Every instruction control flow can reach, from the reset vector outward.

    `sites` finds an access by looking for the bytes that spell one, which works
    only for a long load or store: those carry their bank, so no other encoding
    puts that bank and that address in those positions. An ordinary absolute
    access spells two bytes, and two bytes of data spell an address just as well,
    so the same search would report places the console never touched.

    This asks the other question. It starts where the console starts, follows
    every call, jump and branch it can resolve, and decodes only what control
    flow actually arrives at, so an access it reports is an instruction rather
    than a coincidence. What it cannot follow is a computed jump, which is why
    this finds routines rather than proving there are no others.

    Both paths of a conditional branch are taken, in the order the code lays them
    out, because a routine that polls until a bit sets does its read on the taken
    side and nothing on the other.
    """
    banks = len(rom) // 0x8000
    pending = [(0x00, one, True, True) for one in _entries(rom, entry, banks)]
    seen: set[tuple[int, int]] = set()
    spent = 0

    while pending and spent < limit:
        bank, address, narrow, index = pending.pop()
        while spent < limit:
            spent += 1
            if (bank, address) in seen:
                break
            seen.add((bank, address))
            offset = _offset(bank, address, banks)
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
            if target is not None and _offset(*target, banks) is not None:
                if one.mnemonic in JUMPS:
                    bank, address = target
                    continue
                pending.append((*target, narrow, index))

            if one.mnemonic in LEAVING:
                break
            address += one.size
            if address > 0xFFFF:
                break


def _entries(rom: bytes, entry: int | None, banks: int) -> tuple[int, ...]:
    """Where a sweep starts, which is every vector unless it was told one."""
    if entry is not None:
        return (entry,)
    found = []
    for at in VECTORS:
        address = int.from_bytes(rom[at : at + 2], "little")
        if _offset(0x00, address, banks) is not None and address not in found:
            found.append(address)
    return tuple(found)


def _offset(bank: int, address: int, banks: int) -> int | None:
    """Where a low cartridge keeps that address, or nothing if it keeps it nowhere."""
    if address < 0x8000:
        return None
    slot = bank & 0x7F
    if slot >= banks:
        return None
    return slot * 0x8000 + (address - 0x8000)


def _target(one: Any, bank: int) -> tuple[int, int] | None:
    """Where an instruction sends control, or nothing if it sends it nowhere.

    A branch has to be worked out and a jump only has to be read, which is the
    whole reason this is a function. The disassembler puts the displacement in
    `operand` for a relative mode rather than the address it resolves to, so
    reading it the way a jump is read gives a destination near zero. Every one
    of those falls outside a low cartridge's window and is dropped, so before
    this resolved them the sweep followed no conditional branch at all and said
    in its own docstring that it followed both sides of one.
    """
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
"""How much longer a walk may run than its limit, once callees are counted.

The limit bounds the routine that was asked for, and a callee's instructions are
not the caller's: a guard that spins in a wait loop would otherwise spend the
caller's whole budget and the walk would come back having never reached the
caller's own access. That is not hypothetical. Counting callee instructions
against the limit shortened the longest ST010 exchange from six accesses to
four.

This second bound is the backstop that keeps a runaway descent finite, set far
above anything a real routine needs rather than at what one costs.
"""

DEFAULT_DEPTH = 8
"""How many calls deep a walk will follow before it stops descending.

A bound rather than a budget: a routine that calls eight deep to reach a
coprocessor is not a shape anybody wrote, and without a bound a recursive helper
walks until the instruction limit instead of until the routine ends. The deepest
chain in any cartridge read here is two.
"""


class Frame:
    """Where a walk goes back to when the routine it stepped into returns."""

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
    """Walk a routine from an offset, yielding one step per instruction read.

    A call is followed into the routine it calls and the walk comes back, which
    is what the console does. Until it did, a routine reaching a part only
    through a helper was read as two routines, and the ST018's send routine,
    which is a guard call and then one store, was read as the guard.

    What a return does depends on where the walk is. Inside a callee it goes back
    to the instruction after the call; at the top it ends the routine, because
    there is no caller here to go back to.

    The bank the routine runs in defaults to the one a low cartridge puts that
    offset in, which is the same rule this already uses to work out the address.
    It matters only for an absolute access, where it stands in for a data bank
    register nothing here tracks; see `Step.banked`.
    """
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
"""Instructions no driver routine contains, so decoding one means reading data.

A call whose destination is a jump table, a block of constants or the tail of a
compressed stream still disassembles: every byte is some opcode. What it does not
do is come back, so a walk that descends into it spends its budget on nonsense
and returns nothing. That is not hypothetical either. One F1-ROC II routine calls
into a region that decodes as `brk`, and following it lost the four accesses the
caller made afterwards.
"""


def _returns(rom: bytes, target: tuple[int, int], narrow: bool, banks: int) -> bool:
    """Whether a routine at that address reaches a return without reading nonsense.

    A descent is only safe into a callee that comes back, so this walks it first
    without descending any further. Following a call this cannot prove returns
    would trade the caller's own accesses, which are read, for a callee's, which
    may not be a routine at all.
    """
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
    """Where a call goes, or nothing when it is not a call this can follow."""
    if one.mnemonic not in CALLS:
        return None
    target = _target(one, bank)
    if target is None or _offset(*target, banks) is None:
        return None
    if not _returns(rom, target, narrow, banks):
        return None
    return target
