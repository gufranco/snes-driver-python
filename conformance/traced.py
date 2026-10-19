from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Mapping, Sequence

import collections
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "snes-mapper-python"))

from mapper import header

from conformance import against_cartridges, cartridges, corpus, corroborate

LUA = Path(__file__).resolve().parent / "traced.lua"

EMULATOR = "mame"

FIRMWARE_VARIABLE = "SNES_FIRMWARE_DIR"

ROMPATH_VARIABLE = "MAME_ROMPATH"

PAIR_GAP_SECONDS = 0.0000015

NEVER_APART = 1.0

TIMEOUT_SECONDS = 3600.0

MIRROR = 0x80

RUNG = "emulator"

WHY_NOT = cartridges.WHY_NOT

NOTE = (
    "What a headless MAME run of each cartridge did to its coprocessor's window, one entry per"
    " instruction that reached it. A site is the file offset of the instruction the recorded"
    " program counter ends, found by decoding the cartridge's own bytes at that address under"
    " the recorded M and X flags; its widths are the bytes the bus moved, two when the next"
    " access came from the same instruction at the next address within PAIR_GAP_SECONDS. An"
    " access no single instruction explains, or one whose width the opcode under the recorded"
    " flags contradicts, is kept under disagreements and disputes its site. This is the"
    " emulator rung: a run of an implementation, never a document or the hardware."
)


class Run:
    __slots__ = ("frames", "name", "schedule")

    def __init__(self, name: str, schedule: str, frames: int) -> None:
        self.name = name
        self.schedule = schedule
        self.frames = frames


RUNS = (
    Run("none", "", 3600),
    Run("pressed", "30:3:Start,A,Start,B,Down,A,Up,Start,A,Right", 7200),
)

FIRMWARE = {
    "dsp1b": "d789cb3c36b05c0b23b6c6f23be7aa37c6e78b6ee9ceac8d2d2aa9d8c4d35fa9",
    "dsp2": "03ef4ef26c9f701346708cb5d07847b5203cf1b0818bf2930acd34510ffdd717",
    "dsp3": "0971b08f396c32e61989d1067dddf8e4b14649d548b2188f7c541b03d7c69e4e",
    "dsp4": "752d03b2d74441e430b7f713001fa241f8bbcfc1a0d890ed4143f174dbe031da",
    "st010": "fa9bced838fedea11c6f6ace33d1878024bdd0d02cc9485899d0bdd4015ec24c",
    "st011": "8b2b3f3f3e6e29f4d21d8bc736b400bc988b7d2214ebee15643f01c1fee2f364",
    "st018": "6df209ab5d2524d1839c038be400ae5eb20dafc14a3771a3239cd9e8acd53806",
}

VARIANTS = (
    ("Dungeon Master", "dsp2"),
    ("SD Gundam GX", "dsp3"),
    ("Top Gear 3000", "dsp4"),
    ("Planet's Champ TG 3000", "dsp4"),
    ("Morita Shougi 2", "st018"),
    ("Morita Shougi", "st011"),
    ("F1-ROC II", "st010"),
    ("Exhaust Heat II", "st010"),
)

BY_PART = {"dsp": "dsp1b"}

NEEDS_FIRMWARE = frozenset({"dsp", "st", "st018"})


class Setup:
    __slots__ = ("corpus", "emulator", "firmware", "known", "rompath", "timeout")

    def __init__(
        self,
        emulator: Path | None,
        corpus: Path,
        firmware: Path | None,
        known: Mapping[str, str],
        rompath: str | None,
        timeout: float,
    ) -> None:
        self.emulator = emulator
        self.corpus = corpus
        self.firmware = firmware
        self.known = known
        self.rompath = rompath
        self.timeout = timeout

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Setup:
        held = environment if environment is not None else os.environ
        found = shutil.which(EMULATOR)
        named = held.get(FIRMWARE_VARIABLE)
        return cls(
            emulator=Path(found) if found else None,
            corpus=corpus.PATH,
            firmware=Path(named) if named else None,
            known=FIRMWARE,
            rompath=held.get(ROMPATH_VARIABLE) or None,
            timeout=TIMEOUT_SECONDS,
        )


class Job:
    __slots__ = ("firmware", "identity", "image", "kind", "named", "part")

    def __init__(
        self, identity: Any, image: bytes, part: str, kind: str, named: str | None, firmware: Any
    ) -> None:
        self.identity = identity
        self.image = image
        self.part = part
        self.kind = kind
        self.named = named
        self.firmware: Path | None = firmware


class Trace:
    __slots__ = ("accesses", "closest", "frames", "seconds", "widest")

    def __init__(self, text: str, seconds: float) -> None:
        fields: dict[str, str] = {}
        self.accesses: list[corroborate.Access] = []
        for line in text.splitlines():
            words = line.split()
            if words[0] == "access":
                self.accesses.append(corroborate.Access(words[1:]))
            else:
                fields[words[0]] = words[1]
        self.frames = int(fields["frames"])
        self.widest = float(fields["widest-pair"])
        closest = float(fields["closest-apart"])
        self.closest = None if closest >= NEVER_APART else closest
        self.seconds = seconds


def firmware_name(name: str, part: str) -> str | None:
    for fragment, firmware in VARIANTS:
        if fragment in name:
            return firmware
    return BY_PART.get(part)


def digest_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def firmware_in(directory: Path | None, known: Mapping[str, str]) -> dict[str, Path]:
    if directory is None or not directory.is_dir():
        return {}
    by_digest = {digest: name for name, digest in known.items()}
    found: dict[str, Path] = {}
    for path in sorted(directory.iterdir()):
        name = by_digest.get(digest_of(path))
        if name is not None:
            found.setdefault(name, path)
    return found


def ranges(part: str, kind: str) -> str:
    spans: set[str] = set()
    for window in against_cartridges.windows_under(part, kind):
        low = min(window.data, window.status)
        high = max(window.end, window.status_end)
        for bank in range(window.first_bank, window.last_bank + 1):
            for one in (bank, bank | MIRROR):
                spans.add(f"{one:02X}{low:04X}-{one:02X}{high:04X}")
    return ";".join(sorted(spans))


def prepared(identity: Any, path: Path, firmware: Mapping[str, Path]) -> Job | str:
    image = path.read_bytes()
    part = against_cartridges.part_of(image)
    if part is None:
        return "its header names no part with a window"
    named = firmware_name(identity.name, part)
    held = firmware.get(named) if named is not None else None
    if part in NEEDS_FIRMWARE and held is None:
        return f"{named} firmware is not on hand"
    return Job(identity, image, part, header.read(image).layout, named, held)


OUTPUT_FOLDERS = (
    ("-cfg_directory", "cfg"),
    ("-nvram_directory", "nvram"),
    ("-snapshot_directory", "snap"),
    ("-state_directory", "sta"),
)


def command(setup: Setup, image: Path, scratch: Path) -> list[str]:
    told = [str(setup.emulator), "snes", "-cart", str(image), "-window", "-video", "none"]
    told += ["-sound", "none", "-nothrottle", "-skip_gameinfo", "-autoboot_script", str(LUA)]
    for flag, folder in OUTPUT_FOLDERS:
        told += [flag, str(scratch / folder)]
    return told + (["-rompath", setup.rompath] if setup.rompath else [])


def traced_run(setup: Setup, image: Path, run: Run, spans: str, scratch: Path) -> Trace | None:
    out = scratch / "trace.txt"
    environment = {
        **os.environ,
        "SDL_VIDEODRIVER": "dummy",
        "TRACE_OUT": str(out),
        "TRACE_FRAMES": str(run.frames),
        "TRACE_GAP": f"{PAIR_GAP_SECONDS:.7f}",
        "TRACE_RANGES": spans,
        "TRACE_INPUT": run.schedule,
    }
    started = time.monotonic()
    try:
        done = subprocess.run(
            command(setup, image, scratch),
            cwd=scratch,
            env=environment,
            capture_output=True,
            timeout=setup.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    if done.returncode != 0 or not out.is_file():
        return None
    return Trace(out.read_text(), time.monotonic() - started)


def traces_of(job: Job, setup: Setup) -> list[tuple[Run, Trace]] | None:
    found: list[tuple[Run, Trace]] = []
    with tempfile.TemporaryDirectory() as held:
        image = Path(held) / "image.sfc"
        image.write_bytes(job.image + (job.firmware.read_bytes() if job.firmware else b""))
        spans = ranges(job.part, job.kind)
        for run in RUNS:
            scratch = Path(held) / run.name
            scratch.mkdir()
            trace = traced_run(setup, image, run, spans, scratch)
            if trace is None:
                return None
            found.append((run, trace))
    return found


def flags_of(access: corroborate.Access) -> list[bool]:
    return [access.narrow, access.narrow_index]


def site(offset: int, held: list[corroborate.Verdict]) -> dict[str, Any]:
    agreeing = [one for one in held if one.agrees]
    decoded = agreeing[0].decoded
    assert decoded is not None
    accesses = [one.access for one in agreeing]
    halves = {one.half for one in agreeing}
    return {
        "offset": f"{offset:#08x}",
        "start": f"{decoded.start >> 16:02x}:{decoded.start & 0xFFFF:04x}",
        "mnemonic": decoded.mnemonic,
        "mode": decoded.mode,
        "directions": sorted({one.direction for one in accesses}),
        "widths": sorted({one.width for one in agreeing}),
        "halves": sorted(halves),
        "flags": sorted(map(list, {tuple(flags_of(one)) for one in accesses})),
        "low": f"{min(one.address for one in accesses):06x}",
        "high": f"{max(one.address for one in accesses):06x}",
        "count": sum(one.count for one in accesses),
        "first": min(one.first for one in accesses),
        "disputed": len(agreeing) != len(held),
    }


def sites(verdicts: Iterable[corroborate.Verdict]) -> list[dict[str, Any]]:
    grouped: collections.defaultdict[int, list[corroborate.Verdict]] = collections.defaultdict(list)
    for one in verdicts:
        if one.decoded is not None:
            grouped[one.decoded.offset].append(one)
    return [
        site(offset, held)
        for offset, held in sorted(grouped.items())
        if any(one.agrees for one in held)
    ]


def disagreements(verdicts: Iterable[corroborate.Verdict]) -> list[dict[str, Any]]:
    grouped: collections.defaultdict[tuple[Any, ...], list[corroborate.Access]] = (
        collections.defaultdict(list)
    )
    for one in verdicts:
        if not one.agrees:
            access = one.access
            key = (access.pc, access.direction, access.width, *flags_of(access), one.reason)
            grouped[key].append(access)
    return [
        {
            "pc": f"{pc >> 16:02x}:{pc & 0xFFFF:04x}",
            "direction": direction,
            "width": width,
            "flags": [narrow, narrow_index],
            "low": f"{min(one.address for one in held):06x}",
            "high": f"{max(one.address for one in held):06x}",
            "count": sum(one.count for one in held),
            "reason": reason,
        }
        for (pc, direction, width, narrow, narrow_index, reason), held in sorted(
            grouped.items(), key=lambda item: str(item[0])
        )
    ]


def recorded(job: Job, traces: Sequence[tuple[Run, Trace]], version: str) -> dict[str, Any]:
    verdicts = [
        corroborate.corroborated(job.image, job.kind, access)
        for _run, trace in traces
        for access in trace.accesses
    ]
    firmware = None
    if job.firmware is not None:
        firmware = {"name": job.named, "sha256": digest_of(job.firmware)}
    return {
        "name": job.identity.name,
        "part": job.part,
        "layout": job.kind,
        "rung": RUNG,
        "emulator": f"MAME {version}",
        "firmware": firmware,
        "runs": [
            {
                "input": run.name,
                "schedule": run.schedule or None,
                "frames": trace.frames,
                "seconds": round(trace.seconds, 1),
                "widestPairSeconds": trace.widest,
                "closestApartSeconds": trace.closest,
            }
            for run, trace in traces
        ],
        "sites": sites(verdicts),
        "disagreements": disagreements(verdicts),
    }


LISTED = ("sites", "disagreements")


def entry_text(digest: str, record: Mapping[str, Any]) -> str:
    head = {key: value for key, value in record.items() if key not in LISTED}
    lines = [f'    "{digest}": {{']
    lines += [f"      {json.dumps(key)}: {json.dumps(value)}," for key, value in head.items()]
    for number, key in enumerate(LISTED):
        rows = ",\n".join(f"        {json.dumps(one)}" for one in record.get(key, ()))
        tail = "," if number < len(LISTED) - 1 else ""
        lines.append(
            f'      "{key}": [\n{rows}\n      ]{tail}' if rows else f'      "{key}": []{tail}'
        )
    lines.append("    }")
    return "\n".join(lines)


def written(held: Mapping[str, Any]) -> str:
    entries = ",\n".join(
        entry_text(digest, record) for digest, record in sorted(held["cartridges"].items())
    )
    return (
        f'{{\n  "note": {json.dumps(NOTE)},\n  "rung": "{RUNG}",\n'
        f'  "pairGapSeconds": {PAIR_GAP_SECONDS},\n  "cartridges": {{\n{entries}\n  }}\n}}\n'
    )


def version_of(setup: Setup) -> str:
    done = subprocess.run(
        [str(setup.emulator), "-version"], capture_output=True, text=True, check=False
    )
    return done.stdout.strip()


def summary(record: Mapping[str, Any]) -> str:
    one_width = sum(1 for one in record["sites"] if len(one["widths"]) == 1)
    return (
        f"  {record['name']}: {record['part']}, {len(record['sites'])} sites,"
        f" {one_width} with one width, {len(record['disagreements'])} disagreements"
    )


def jobs_for(present: Iterable[tuple[Any, Path]], setup: Setup) -> tuple[list[Job], list[str]]:
    firmware = firmware_in(setup.firmware, setup.known)
    jobs: list[Job] = []
    skipped: list[str] = []
    for identity, path in present:
        found = prepared(identity, path, firmware)
        if isinstance(found, str):
            skipped.append(f"    skipped: {identity.name}, {found}")
        else:
            jobs.append(found)
    return jobs, skipped


def traced_all(jobs: Sequence[Job], setup: Setup) -> list[list[tuple[Run, Trace]] | None]:
    workers = max(1, (os.cpu_count() or 2) // 2)
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        return list(pool.map(lambda job: traces_of(job, setup), jobs))


def main(
    argv: Sequence[str], catalogue: Mapping[str, Any] | None = None, setup: Setup | None = None
) -> int:
    told = setup if setup is not None else Setup.from_environment()
    where = Path(argv[0]) if argv else None
    present = cartridges.present(where, catalogue)
    if told.emulator is None:
        print(f"  no {EMULATOR} on this machine: {len(present)} cartridges not traced")
        return 2
    if not present:
        print(f"  no cartridge was found under {where or cartridges.directory()}")
        print(f"  {WHY_NOT}")
        return 2
    jobs, skipped = jobs_for(present, told)
    for line in skipped:
        print(line)
    version = version_of(told)
    held = corpus.load(told.corpus)
    failed = 0
    for job, traces in zip(jobs, traced_all(jobs, told), strict=True):
        if traces is None:
            print(f"    failed: {job.identity.name}")
            failed += 1
            continue
        record = recorded(job, traces, version)
        held["cartridges"][job.identity.sha256] = record
        print(summary(record))
    told.corpus.write_text(written(held))
    print(f"  {len(jobs) - failed} cartridges traced")
    if failed:
        return 1
    return 0 if jobs else 2


def entry() -> int:
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    entry()
