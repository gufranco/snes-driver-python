from __future__ import annotations

import collections
from typing import TYPE_CHECKING, Any

from snesdriver import walk

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

    from snesdriver.walk import Flags, Saved

Entry = tuple[int, int, "Flags"]

Node = tuple[int, int, "Flags", "Saved", Entry]

Back = tuple[int, int, "Saved", Entry]

VECTORS = (0xFFE4, 0xFFE6, 0xFFE8, 0xFFEA, 0xFFEE, 0xFFF4, 0xFFF8, 0xFFFA, 0xFFFC, 0xFFFE)

EMULATION_VECTORS = 0xFFF0

EVERYWHERE_LIMIT = 400000

TOP = 0xFFFF


class Sweep:
    __slots__ = (
        "abandoned",
        "backs",
        "banks",
        "exits",
        "found",
        "kind",
        "limit",
        "pending",
        "rom",
        "seen",
        "spent",
    )

    def __init__(self, rom: bytes, kind: str, limit: int) -> None:
        self.rom = rom
        self.kind = kind
        self.banks = len(rom) // walk.BANK
        self.limit = limit
        self.spent = 0
        self.pending: list[Node] = []
        self.seen: set[Node] = set()
        self.exits: collections.defaultdict[Entry, set[Flags]] = collections.defaultdict(set)
        self.backs: collections.defaultdict[Entry, set[Back]] = collections.defaultdict(set)
        self.abandoned: set[Entry] = set()
        self.found: collections.defaultdict[int, set[Flags]] = collections.defaultdict(set)

    def start(self, address: int, state: Flags) -> None:
        self.push((0x00, address, state, (), (0x00, address, state)))

    def push(self, node: Node) -> None:
        if node not in self.seen:
            self.seen.add(node)
            self.pending.append(node)

    def run(self) -> Iterator[walk.Step]:
        while self.spent < self.limit and self.refilled():
            self.spent += 1
            step = self.visit(self.pending.pop())
            if step is not None:
                yield step

    def refilled(self) -> bool:
        if not self.pending:
            for entry in [one for one in self.backs if not self.exits.get(one)]:
                if entry not in self.abandoned:
                    self.abandoned.add(entry)
                    self.returned(entry, walk.UNKNOWN)
        return bool(self.pending)

    def visit(self, node: Node) -> walk.Step | None:
        bank, address, state, _saved, _entry = node
        offset = walk.offset_of(bank, address, self.banks, self.kind)
        if offset is None:
            return None
        one = walk.decoded(self.rom, offset, address, state)
        if one is None:
            return None
        self.found[one.offset].add(state)
        if not walk.unplaceable(one, state):
            self.follow(node, one)
        return walk.Step(one, state[0], bank)

    def follow(self, node: Node, one: Any) -> None:
        bank, address, before, saved, entry = node
        state, saved = walk.flags(one, before, saved)
        if one.mnemonic in walk.RETURNING:
            self.exited(entry, state)
            return
        target = self.inside(walk.target_of(one, bank))
        if one.mnemonic in walk.CALLS:
            self.called(target, (bank, address + one.size, saved, entry), state)
            return
        if target is not None:
            self.push((*target, state, saved, entry))
        if one.mnemonic not in walk.LEAVING:
            self.resume((bank, address + one.size, saved, entry), state)

    def inside(self, target: tuple[int, int] | None) -> tuple[int, int] | None:
        if target is None or walk.offset_of(*target, self.banks, self.kind) is None:
            return None
        return target

    def called(self, target: tuple[int, int] | None, back: Back, state: Flags) -> None:
        if target is None:
            self.resume(back, walk.UNKNOWN)
            return
        callee = (*target, state)
        self.push((*target, state, (), callee))
        self.backs[callee].add(back)
        for left in tuple(self.exits.get(callee, ())):
            self.resume(back, left)

    def exited(self, entry: Entry, state: Flags) -> None:
        if state not in self.exits[entry]:
            self.exits[entry].add(state)
            self.returned(entry, state)

    def returned(self, entry: Entry, state: Flags) -> None:
        for back in tuple(self.backs.get(entry, ())):
            self.resume(back, state)

    def resume(self, back: Back, state: Flags) -> None:
        bank, address, saved, entry = back
        if address <= TOP:
            self.push((bank, address, state, saved, entry))


def entry_flags(vector: int | None) -> Flags:
    return walk.EMULATION if vector is not None and vector >= EMULATION_VECTORS else walk.UNKNOWN


def entries(
    rom: bytes, entry: int | None, banks: int, kind: str = walk.DEFAULT_LAYOUT
) -> tuple[tuple[int | None, int], ...]:
    if entry is not None:
        return ((None, entry),)
    found: list[tuple[int | None, int]] = []
    for vector in VECTORS:
        at = walk.offset_of(0x00, vector, banks, kind)
        if at is None:
            continue
        address = int.from_bytes(rom[at : at + 2], "little")
        if (
            walk.offset_of(0x00, address, banks, kind) is not None
            and (vector, address) not in found
        ):
            found.append((vector, address))
    return tuple(found)


def swept(
    rom: bytes,
    entry: int | None = None,
    limit: int = EVERYWHERE_LIMIT,
    kind: str = walk.DEFAULT_LAYOUT,
) -> Sweep:
    sweep = Sweep(rom, kind, limit)
    for vector, address in entries(rom, entry, sweep.banks, kind):
        sweep.start(address, entry_flags(vector))
    return sweep


def everywhere(
    rom: bytes,
    entry: int | None = None,
    limit: int = EVERYWHERE_LIMIT,
    kind: str = walk.DEFAULT_LAYOUT,
) -> Iterator[walk.Step]:
    yield from swept(rom, entry, limit, kind).run()


def contexts(
    rom: bytes,
    kind: str = walk.DEFAULT_LAYOUT,
    entry: int | None = None,
    limit: int = EVERYWHERE_LIMIT,
) -> dict[int, frozenset[Flags]]:
    sweep = swept(rom, entry, limit, kind)
    for _ in sweep.run():
        pass
    return {offset: frozenset(held) for offset, held in sweep.found.items()}
