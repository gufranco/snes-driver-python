"""Look at this machine and say what is actually here, so a report can be believed.

What goes wrong with this package is rarely a defect in it. It is a submodule
that was never checked out, a cartridge library that was never put where the
checks look, or a library that is there and holds files nothing recognises. All
three look the same from outside: the run is green and it proved less than the
reader thinks.

The submodule is the sharp one. Every claim here about a driver routine was read
by disassembling one, and the disassembler lives in another repository carried as
a submodule. A checkout without `--recurse-submodules` leaves the directory there
and empty, and what fails is an import rather than a check.

Which is why nothing is imported from the package at the top of this file, and
why this is run as a file rather than with `-m`. Either entry point reads the
package's own `__init__` first, and that is the import that fails. Run it as

    python3 snesdriver/doctor.py

and every import that can fail happens inside the finding that needs it, where
its failure is the report rather than the end of it.

Two rules shape it, and they are the whole point.

Nothing is hidden. A check that fails says what it saw, and a check that itself
throws is caught and reported as what it threw, named by its type. An absent
library is reported as absent rather than as a failure, because a fresh checkout
has none and that is the normal state, but it is never reported as nothing at all.

Nothing is inferred. Every line is something looked at on this machine just now,
including a conversation actually walked out of bytes assembled here rather than
a claim that the walker imports.
"""

from __future__ import annotations

import json
import os
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Mapping, Sequence


def _version(where: Path | None = None) -> str:
    """The package version, read out of the file beside this one.

    Read rather than imported. Importing it would go through the package, and
    the package is what fails on the machine this exists to diagnose.
    """
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = _version()


def _loaded() -> Any:
    """The package, imported now rather than when this file was read.

    Imported by name rather than relatively, and with the repository put on the
    path first, because this file is run as a script and a relative import has
    no package to be relative to. A single place for it, so every finding fails
    the same way when a submodule is absent.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    for one in SUBMODULES:
        if str(ROOT / one) not in sys.path:
            sys.path.append(str(ROOT / one))
    from snesdriver import walk, windows

    return walk, windows


ROOT = Path(__file__).resolve().parent.parent

MANIFEST = ROOT / "cartridges.manifest.json"

DIRECTORY_VARIABLE = "SNES_CARTRIDGE_DIR"

DEFAULT_DIRECTORY = ROOT / "cartridges"

ALONGSIDE = ROOT.parent / "cartridges"

READABLE_SUFFIXES = (".sfc", ".smc")

SUBMODULES = ("mos65xx-python", "snes-mapper-python")

OLDEST_PYTHON = (3, 12)

PROBE_LAYOUT = "lorom"

PROBE_PART = "dsp"


class Finding:
    """One thing that was looked at, and what was there."""

    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        """The same, with what to do about it when there is something to do."""
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python() -> Finding:
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package() -> Finding:
    return Finding("snesdriver", True, f"version {VERSION}")


def _window(part: str, layout: str) -> Finding:
    """Where a part answers under a layout, which is the package in one line."""
    try:
        _, windows = _loaded()
        found = windows.window_for(part, layout)
    except Exception as trouble:
        return Finding(f"{part} under {layout}", False, f"{type(trouble).__name__}: {trouble}")
    if found is None:
        return Finding(
            f"{part} under {layout}",
            False,
            "no window, and every published pair should have one",
            "a pair the package publishes and cannot answer for is a defect here",
        )
    return Finding(
        f"{part} under {layout}",
        True,
        f"banks {found.first_bank:#04x} to {found.last_bank:#04x},"
        f" data {found.data:#06x}, status {found.status:#06x}",
    )


def _routine(window: Any) -> bytes:
    """A driver routine assembled here, so the walk has something real to read.

    Written rather than borrowed. A routine taken out of a cartridge would put a
    fragment of somebody's ROM in this file, and the walk only needs a load, a
    store into the window and a return to have something to follow.
    """
    return bytes(
        (
            0xA9,
            0x42,
            0x8D,
            window.data & 0xFF,
            window.data >> 8,
            0xAD,
            window.status & 0xFF,
            window.status >> 8,
            0x60,
        )
    )


def _walking(part: str = PROBE_PART, layout: str = PROBE_LAYOUT) -> Finding:
    """That a conversation is walked out of bytes, not merely that walk imports."""
    try:
        walk, windows = _loaded()
        found = windows.window_for(part, layout)
        if found is None:  # pragma: no cover
            return Finding("walking a routine", False, f"no {part} window under {layout}")
        held = list(walk.through(_routine(found), 0, address=0x8000))
    except Exception as trouble:
        return Finding(
            "walking a routine",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "the walker failed on a routine assembled here, so nothing it says"
            " about a real cartridge can be trusted from this machine",
        )
    return Finding(
        "walking a routine",
        bool(held),
        f"{len(held)} steps read out of {len(_routine(found))} bytes assembled here",
        "a routine that walks to nothing means the disassembler under this is not"
        " answering; check the mos65xx-python submodule below",
    )


def _submodule(name: str, root: Path = ROOT) -> Finding:
    """Whether a submodule is checked out, since its absence is silent otherwise.

    The marker is the manifest rather than the directory. Git creates the empty
    directory for a submodule it has not fetched, so a check on the path alone
    reports a present submodule on exactly the machine where it is missing.
    """
    where = root / name
    if (where / "pyproject.toml").is_file():
        return Finding(f"submodule {name}", True, f"checked out at {where}")
    return Finding(
        f"submodule {name}",
        False,
        f"{where} is empty" if where.is_dir() else f"{where} is not there",
        "the checks that read a real cartridge import from this and will skip"
        " rather than run; git submodule update --init --recursive",
    )


def _manifest(path: Path | str = MANIFEST) -> Finding:
    """How many cartridges the manifest names, or why it could not be read."""
    try:
        held = json.loads(Path(path).read_text())
    except OSError as trouble:
        return Finding(
            "manifest",
            False,
            f"could not be read: {trouble}",
            "the manifest names every cartridge carrying one of these parts;"
            " without it the check against a real library cannot run at all",
        )
    except ValueError as trouble:
        return Finding(
            "manifest",
            False,
            f"is not readable as JSON: {trouble}",
            "the file is here and damaged, which is worse than absent",
        )
    named = held.get("cartridges") or []
    return Finding(
        "manifest",
        bool(named),
        f"{len(named)} cartridges named",
        "a manifest naming nothing identifies nothing",
    )


def _looking(environment: Mapping[str, str] | None = None) -> list[Finding]:
    """Everywhere a cartridge is looked for, and which of them is chosen.

    Reported as its own line because a named directory wins even when it is
    empty, which is deliberate and surprising: a typo in the variable becomes a
    run that finds nothing and says so, rather than one that silently falls back
    and reports a pass over the wrong library.
    """
    held = environment if environment is not None else os.environ
    named = held.get(DIRECTORY_VARIABLE)
    places = [*([Path(named)] if named else []), DEFAULT_DIRECTORY, ALONGSIDE]
    chosen = (
        Path(named) if named else next((one for one in places if one.is_dir()), DEFAULT_DIRECTORY)
    )
    return [
        Finding(
            DIRECTORY_VARIABLE,
            True,
            f"set to {named}" if named else "not set, so the places below are tried in order",
        ),
        Finding("looking in", True, ", ".join(str(one) for one in places)),
        Finding("chosen", True, str(chosen)),
    ]


def _library(where: Path | str) -> Finding:
    """Whether a library is there, and whether it holds anything readable.

    The count of files is the line that matters. A directory that exists and
    holds nothing reads as a present library to anything that only checks the
    path, and the check against real cartridges then runs over nothing and
    reports a pass.
    """
    place = Path(where)
    if not place.is_dir():
        return Finding(
            "library",
            True,
            f"none at {place}, so the check against real cartridges will skip rather than run",
        )
    try:
        present = [
            one
            for one in place.rglob("*")
            if one.suffix.lower() in READABLE_SUFFIXES and one.is_file()
        ]
    except OSError as trouble:
        return Finding("library", False, f"could not be read: {trouble}")
    return Finding(
        "library",
        bool(present),
        f"{len(present)} images at {place}"
        if present
        else f"{place} is here and holds nothing this package reads",
        "a directory that is present and empty reads as a library to anything that"
        " only checks the path; either fill it or unset the variable",
    )


def examine(
    environment: Mapping[str, str] | None = None,
    manifest: Path | str = MANIFEST,
    root: Path = ROOT,
) -> list[Finding]:
    """Everything worth looking at on this machine, in the order a reader wants it."""
    found = [_python(), _package()]
    try:
        _, windows = _loaded()
        pairs = [
            (part, layout)
            for part, layouts in sorted(windows.WINDOWS.items())
            for layout in sorted(layouts)
        ]
    except Exception as trouble:
        pairs = []
        found.append(
            Finding(
                "windows",
                False,
                f"{type(trouble).__name__}: {trouble}",
                "the package could not be imported at all, so nothing below it"
                " could be looked at; the submodule lines say why",
            )
        )
    found.extend(_window(part, layout) for part, layout in pairs)
    found.append(_walking())
    found.extend(_submodule(name, root) for name in SUBMODULES)
    found.append(_manifest(manifest))
    where = _looking(environment)
    found.extend(where)
    found.append(_library(where[-1].detail))
    return found


def report(found: Sequence[Finding]) -> list[str]:
    """The lines a person pastes into an issue."""
    unwell = [one for one in found if not one.ok]
    lines = [f"snesdriver {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list[Finding]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
