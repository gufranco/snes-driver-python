from __future__ import annotations

import importlib.util
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
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = _version()


def _loaded() -> Any:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    for one in SUBMODULES:
        if str(ROOT / one) not in sys.path:
            sys.path.append(str(ROOT / one))
    from snesdriver import walk, windows

    return walk, windows


ROOT = Path(__file__).resolve().parent.parent

ENVIRONMENT = Path(__file__).resolve().parent / "environment.py"


def _environment() -> Any:
    spec = importlib.util.spec_from_file_location("snesdriver_doctor_environment", ENVIRONMENT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
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
    held = environment if environment is not None else os.environ
    named = held.get(DIRECTORY_VARIABLE)
    places = [*([Path(named)] if named else []), ALONGSIDE, DEFAULT_DIRECTORY]
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


def _library(where: Path | str, shipped: Path = DEFAULT_DIRECTORY) -> Finding:
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
    if not present and place == shipped:
        return Finding(
            "library",
            True,
            f"{place} holds no images yet, so the check against real cartridges will skip"
            " rather than run",
        )
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
    unwell = [one for one in found if not one.ok]
    lines = [f"snesdriver {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(_environment().lines(ROOT))
    lines.append("")
    lines.append("  this package")
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
