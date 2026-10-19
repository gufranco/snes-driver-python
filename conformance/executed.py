from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

import collections
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "mos65xx-python"))
sys.path.append(str(ROOT / "snes-mapper-python"))

from mapper import header, layout
from mos65xx import Cpu

from conformance import against_cartridges

DEFAULT_BUDGET = 2_000_000

NMI_EVERY = 20_000

BLANKING = frozenset({0x4210, 0x4212})

BLANKING_BIT = 0x80

WORK_RAM_BYTES = 0x20000

SAVE_RAM_BYTES = 0x80000

LOW_WORK_RAM = 0x1FFF

WORK_RAM_BANKS = (0x7E, 0x7F)

USAGE = "usage: python3 -m conformance.executed <image> [budget] [--widths]"

WIDTHS = "--widths"

Touched = collections.Counter[tuple[int, int, int, str]]

Flags = tuple[bool, bool]


class Console:
    def __init__(self, rom: bytes, kind: str, window: Any, seed: int) -> None:
        scrambled = random.Random(seed)
        self.rom = rom
        self.kind = kind
        self.window = window
        self.work = bytearray(scrambled.randbytes(WORK_RAM_BYTES))
        self.save = bytearray(scrambled.randbytes(SAVE_RAM_BYTES))
        self.blanking = 0
        self.running = (0, 0)
        self.flags: Flags = (True, True)
        self.touched: Touched = collections.Counter()
        self.widths: collections.defaultdict[tuple[int, int], set[Flags]] = collections.defaultdict(
            set
        )

    def work_index(self, address: int) -> int:
        bank = address >> 16
        if bank in WORK_RAM_BANKS:
            return ((bank & 1) << 16) | (address & 0xFFFF)
        return address & LOW_WORK_RAM

    def note(self, address: int, direction: str) -> None:
        if self.window.reaches(address >> 16, address & 0xFFFF):
            self.touched[(*self.running, address, direction)] += 1
            self.widths[self.running].add(self.flags)

    def read8(self, address: int) -> int:
        self.note(address, "read")
        found = layout.resolve(self.kind, address)
        if found.region == layout.ROM and found.offset is not None:
            at: int = found.offset % len(self.rom)
            return self.rom[at]
        if found.region == layout.WORK_RAM:
            return self.work[self.work_index(address)]
        if found.region == layout.SAVE_RAM:
            return self.save[address % SAVE_RAM_BYTES]
        if address & 0xFFFF in BLANKING:
            self.blanking ^= BLANKING_BIT
            return self.blanking
        return 0

    def write8(self, address: int, value: int) -> None:
        self.note(address, "write")
        found = layout.resolve(self.kind, address)
        if found.region == layout.WORK_RAM:
            self.work[self.work_index(address)] = value
        elif found.region == layout.SAVE_RAM:
            self.save[address % SAVE_RAM_BYTES] = value


def run(
    rom: bytes,
    window: Any,
    kind: str = layout.LOROM,
    budget: int = DEFAULT_BUDGET,
    seed: int = 0,
) -> tuple[int, Console]:
    console = Console(rom, kind, window, seed)
    cpu: Any = Cpu("65816", console, seed=seed)
    cpu.reset()
    steps = 0
    while steps < budget:
        if cpu.held() and not cpu.waiting:
            break
        if cpu.waiting or (steps and steps % NMI_EVERY == 0):
            cpu.nmi()
        console.running = (cpu.pb, cpu.pc)
        console.flags = (bool(cpu.m8), bool(cpu.x8))
        cpu.step()
        steps += 1
    return steps, console


def executed(
    rom: bytes,
    window: Any,
    kind: str = layout.LOROM,
    budget: int = DEFAULT_BUDGET,
    seed: int = 0,
) -> tuple[int, Touched]:
    steps, console = run(rom, window, kind, budget, seed)
    return steps, console.touched


def ran(
    rom: bytes,
    window: Any,
    kind: str = layout.LOROM,
    budget: int = DEFAULT_BUDGET,
    seed: int = 0,
) -> dict[int, frozenset[Flags]]:
    _steps, console = run(rom, window, kind, budget, seed)
    found: collections.defaultdict[int, set[Flags]] = collections.defaultdict(set)
    for (bank, pc), held in console.widths.items():
        offset = offset_of(kind, bank, pc)
        if offset is not None:
            found[offset] |= held
    return {offset: frozenset(held) for offset, held in found.items()}


def printed(widths: dict[int, frozenset[Flags]]) -> str:
    return json.dumps(
        {
            f"{offset:#08x}": sorted([*state] for state in held)
            for offset, held in sorted(widths.items())
        }
    )


def offset_of(kind: str, bank: int, address: int) -> int | None:
    found: int | None = layout.resolve(kind, (bank << 16) | address).offset
    return found


def report(kind: str, steps: int, touched: Touched) -> list[str]:
    routines = sorted({(bank, pc) for bank, pc, _address, _direction in touched})
    lines = [f"  {steps} instructions run, {len(routines)} instructions reached the part"]
    for bank, pc in routines:
        offset = offset_of(kind, bank, pc)
        where = "-" if offset is None else f"{offset:#08x}"
        reached = sorted(
            {
                f"{direction} {address:06x}"
                for one, at, address, direction in touched
                if (one, at) == (bank, pc)
            }
        )
        lines.append(f"    {bank:02x}:{pc:04x} at {where}: {', '.join(reached)}")
    return lines


def joined(
    image: bytes, windows: Sequence[Any], kind: str, budget: int
) -> dict[int, frozenset[Flags]]:
    found: dict[int, frozenset[Flags]] = {}
    for window in windows:
        for offset, held in ran(image, window, kind, budget).items():
            found[offset] = found.get(offset, frozenset()) | held
    return found


def main(argv: Sequence[str]) -> int:
    told = [one for one in argv if one != WIDTHS]
    if not told:
        print(USAGE)
        return 2
    image = Path(told[0]).read_bytes()
    budget = int(told[1]) if len(told) > 1 else DEFAULT_BUDGET
    found = header.read(image)
    part = against_cartridges.part_of(image)
    windows = [] if part is None else against_cartridges.windows_under(part, found.layout)
    if not windows:
        print(f"  {told[0]} carries no part this package has a window for")
        return 1
    if WIDTHS in argv:
        print(printed(joined(image, windows, found.layout, budget)))
        return 0
    for window in windows:
        steps, touched = executed(image, window, found.layout, budget)
        print(f"  {part} {window!r}")
        for line in report(found.layout, steps, touched):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
