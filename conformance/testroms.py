from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import executed
from snesdriver import reached, sites, window_for

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

HERE = Path(__file__).resolve().parent

RECORD = HERE / "testroms.json"

MEASURED = HERE / "testroms_measured.json"

RECORDING = "--record"

DEFAULT_BUDGET = 500_000

Measures = dict[str, dict[str, Any]]


def measure(image: bytes, part: str, layout: str, budget: int) -> dict[str, Any]:
    window = window_for(part, layout)
    assert window is not None, f"the record names {part} under {layout}, where it has no window"
    ran, touched = executed.executed(image, window, layout, budget)
    return {
        "budget": budget,
        "ran": ran,
        "instructions": len({(bank, pc) for bank, pc, _address, _direction in touched}),
        "dataBanks": sorted({f"{address >> 16:02x}" for _b, _p, address, _d in touched}),
        "longSites": len(sites(image, window)),
        "reachedByWalk": len(reached(image, window, kind=layout)),
    }


def measured_in(folder: Path, record: Path, budget: int) -> Measures:
    listed = {one["sha256"]: one for one in json.loads(record.read_text())["cartridges"]}
    found: Measures = {}
    if not folder.is_dir():
        return found
    for path in sorted(one for one in folder.iterdir() if one.is_file()):
        image = path.read_bytes()
        entry = listed.get(hashlib.sha256(image).hexdigest())
        if entry is not None:
            found[entry["id"]] = measure(image, entry["part"], entry["layout"], budget)
    return found


def main(
    argv: Sequence[str],
    say: Callable[[str], object] = print,
    record: Path = RECORD,
    measured: Path = MEASURED,
) -> int:
    told = [one for one in argv if one != RECORDING]
    total = len(json.loads(record.read_text())["cartridges"])
    if not told:
        say(f"  0 of {total} test images examined: no folder was named")
        return 2
    budget = int(told[1]) if len(told) > 1 else DEFAULT_BUDGET
    found = measured_in(Path(told[0]), record, budget)
    say(f"  {len(found)} of {total} test images examined")
    if not found:
        return 2
    if RECORDING in argv:
        measured.write_text(json.dumps(found, indent=2, sort_keys=True) + "\n")
        return 0
    held = json.loads(measured.read_text())
    moved = [name for name, one in sorted(found.items()) if held.get(name) != one]
    for name in moved:
        say(f"  ! {name}: measured {found[name]}, recorded {held.get(name)}")
    return 1 if moved else 0


def entry() -> int:
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    entry()
