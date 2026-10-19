from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent / "traced.json"


def load(path: Path | None = None) -> dict[str, Any]:
    where = path or PATH
    if not where.is_file():
        return {"cartridges": {}}
    held = json.loads(where.read_text())
    assert isinstance(held, dict), f"{where} does not hold an object"
    return held


def widths(digest: str, held: Mapping[str, Any] | None = None) -> dict[int, int]:
    cartridge = (held if held is not None else load())["cartridges"].get(digest)
    if cartridge is None:
        return {}
    return {
        int(site["offset"], 16): site["widths"][0]
        for site in cartridge["sites"]
        if len(site["widths"]) == 1 and not site["disputed"]
    }
