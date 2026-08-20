"""Cartridges their owner supplies, identified before any of them is read.

What this package reads is the driver routine inside a cartridge, so a cartridge
is the input rather than a test fixture. A file that is not the one named would
be disassembled anyway and would report a protocol nobody's hardware has, which
is worse than reporting nothing.

Every file is checked against all four of its digests rather than only the one that
decides. A file can be the right length under the right name and still be a bad
dump, and a manifest that publishes a crc32 beside a sha256 and then never looks at
the crc32 is publishing decoration.

Only retail releases are listed. A modified release can carry altered code, and a
driver routine read out of one describes somebody's edit rather than the part.

Nothing here carries any part of a cartridge. A name, a length and four digests are
measurements, and a digest reconstructs nothing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Iterable, Iterator, Mapping

import hashlib
import json
import os
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MANIFEST = ROOT / "cartridges.manifest.json"

DIRECTORY_VARIABLE = "SNES_CARTRIDGE_DIR"

DEFAULT_DIRECTORY = ROOT / "cartridges"

ALONGSIDE = ROOT.parent / "cartridges"
"""Where a project carrying this one as a submodule keeps its own library.

Standalone, the directory in this repository is the one that matters. As a
submodule the parent owns the library, and asking its owner for a second copy of
four gigabytes because the path moved is not a reasonable thing to do.
"""

READABLE_SUFFIXES = (".sfc", ".smc")

DIGESTS = ("crc32", "md5", "sha1", "sha256")

DECIDES = "sha256"

DIGEST_WIDTHS = {"crc32": 8, "md5": 32, "sha1": 40, "sha256": 64}

WHY_NOT = (
    "no cartridge was found: these tests read the header of a real cartridge, and a"
    " cartridge belongs to whoever made it, so copies you already own go in the"
    f" cartridges directory of this repository or wherever {DIRECTORY_VARIABLE} points"
)


class Unrecognised(Exception):
    pass


class Corrupt(Exception):
    pass


class Identity:
    """What a cartridge turned out to be."""

    def __init__(
        self,
        name: str,
        title: str,
        size: int,
        layout: str,
        chipset: str,
        sha256: str,
    ) -> None:
        self.name = name
        self.title = title
        self.size = size
        self.layout = layout
        self.chipset = chipset
        self.sha256 = sha256

    @override
    def __repr__(self) -> str:
        return f"<Identity {self.name}, {self.title}, {self.size} bytes>"


def digests_of(image: bytes) -> dict[str, str]:
    """Every digest this manifest publishes, for one file."""
    return {
        "crc32": f"{zlib.crc32(image) & 0xFFFFFFFF:08x}",
        "md5": hashlib.md5(image).hexdigest(),
        "sha1": hashlib.sha1(image).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


def manifest(path: Path | str | None = None) -> dict[str, Any]:
    with Path(path or MANIFEST).open() as handle:
        held = json.load(handle)
    assert isinstance(held, dict), f"{path or MANIFEST} does not hold an object"
    return held


def directories(environment: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    """Everywhere a cartridge is looked for, nearest intent first."""
    named = (environment if environment is not None else os.environ).get(DIRECTORY_VARIABLE)
    places = [Path(named)] if named else []
    return (*places, DEFAULT_DIRECTORY, ALONGSIDE)


def directory(
    environment: Mapping[str, str] | None = None, places: Iterable[Path] | None = None
) -> Path:
    """Where to look: what was named, or the first place that is actually there.

    A named directory wins even when it is empty or missing. Quietly falling back
    from a path somebody typed turns their typo into a run that skips its tests and
    reports success, which is the failure this whole file exists to avoid.
    """
    named = (environment if environment is not None else os.environ).get(DIRECTORY_VARIABLE)
    if named:
        return Path(named)
    for place in places if places is not None else directories(environment):
        if place.is_dir():
            return place
    return DEFAULT_DIRECTORY


def identify(image: bytes, catalogue: Mapping[str, Any] | None = None) -> Identity:
    """Which cartridge this is, or why it is not one the manifest knows."""
    found = digests_of(image)
    entries = (catalogue or manifest())["cartridges"]

    for entry in entries:
        if entry[DECIDES] != found[DECIDES]:
            continue
        _confirm(entry, found)
        return Identity(
            name=entry["name"],
            title=entry["title"],
            size=entry["bytes"],
            layout=entry["layout"],
            chipset=entry["chipset"],
            sha256=entry[DECIDES],
        )

    raise Unrecognised(_diagnosis(image, found, entries))


def _confirm(entry: Mapping[str, Any], found: Mapping[str, str]) -> None:
    """Every other digest the manifest publishes has to agree as well.

    Reaching here means the deciding digest already matched, so a disagreement is
    not a different file: it is a manifest contradicting itself, which is worth
    saying out loud rather than passing over.
    """
    for name in DIGESTS:
        if name == DECIDES or name not in entry:
            continue
        if entry[name].lower() != found[name]:
            raise Corrupt(
                f"{entry['name']} matches on {DECIDES} but not on {name}:"
                f" the manifest says {entry[name]} and the file gives {found[name]}."
                " A manifest that disagrees with itself was edited by hand or built"
                " from two different copies"
            )


REPAIRS: tuple[tuple[str, Callable[[bytes], bytes]], ...] = (
    (
        "strip the first 512 bytes, which is a copier header",
        lambda image: image[512:],
    ),
    (
        "strip the last 512 bytes",
        lambda image: image[:-512] if len(image) > 512 else image,
    ),
    (
        "swap every pair of bytes, which undoes a byte-order change",
        lambda image: bytes(image[at ^ 1] for at in range(len(image) - len(image) % 2)),
    ),
)
"""Lossless things that can be done to a file the user already has.

Nothing is ever suggested on a hunch: a transform is named only after it has been
applied and its result has matched a published digest. A repair that has not been
confirmed is a guess about somebody's file.
"""


def repairs(image: bytes, entries: Iterable[Mapping[str, Any]]) -> list[tuple[str, str]]:
    """Every transform of this file that turns it into a cartridge the manifest knows."""
    accepted = {entry[DECIDES]: str(entry["name"]) for entry in entries}
    found = []
    for how, apply in REPAIRS:
        changed = apply(image)
        if not changed or changed == image:
            continue
        digest = hashlib.sha256(changed).hexdigest()
        if digest in accepted:
            found.append((how, accepted[digest]))
    return found


def _diagnosis(image: bytes, found: Mapping[str, str], entries: Iterable[Mapping[str, Any]]) -> str:
    entries = list(entries)

    fixable = repairs(image, entries)
    if fixable:
        how, name = fixable[0]
        return (
            f"this is not a cartridge the manifest knows, but {how} turns it into"
            f" {name}. That was checked rather than guessed: the change was applied"
            " and the result matched the published sha256. Do it to your own copy"
            " and try again"
        )

    known_bad = [
        entry
        for entry in entries
        for one in entry.get("badDumps", ())
        if one.get(DECIDES) == found[DECIDES]
    ]
    if known_bad:
        return (
            f"this is a known bad dump of {known_bad[0]['name']}: its sha256"
            f" {found[DECIDES]} is recorded in the manifest as damaged rather than"
            " as unrecognised. The copy is the problem, not the name it was given"
        )

    same_length = [entry for entry in entries if entry["bytes"] == len(image)]

    if same_length:
        names = ", ".join(entry["name"] for entry in same_length[:3])
        return (
            f"this is {len(image)} bytes, the length of {names}, but its content is"
            f" altered: its sha256 is {found['sha256']} and no cartridge listed has"
            " that. A file of the right length with the wrong content is usually a"
            " modified release, a translation, or a bad dump"
        )

    return (
        f"this is {len(image)} bytes and no cartridge listed has that length."
        f" Its sha256 is {found['sha256']}, its crc32 is {found['crc32']}."
        " A file a few hundred bytes longer than a round number carries a copier stub"
    )


def found(
    where: Path | str | None = None, catalogue: Mapping[str, Any] | None = None
) -> Iterator[tuple[Identity, Path]]:
    """Every cartridge on disk the manifest recognises, with the file it came from."""
    where = Path(where) if where is not None else directory()
    if not where.is_dir():
        return

    catalogue = catalogue or manifest()
    for path in sorted(where.rglob("*")):
        if path.suffix.lower() not in READABLE_SUFFIXES or not path.is_file():
            continue
        try:
            yield identify(path.read_bytes(), catalogue), path
        except Unrecognised:
            continue


def present(
    where: Path | str | None = None, catalogue: Mapping[str, Any] | None = None
) -> tuple[tuple[Identity, Path], ...]:
    return tuple(found(where, catalogue))
