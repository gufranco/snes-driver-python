"""Read what a cartridge says to its coprocessor, out of the cartridge's own code.

A coprocessor's protocol is written down in exactly one place: the routine the
cartridge runs to drive it. Most of these parts have no surviving datasheet, and
the emulators that talk to them were written by people who read that same code.

    from snesdriver import shapes, window_for

    window = window_for("dsp", "hirom")
    shapes(open("game.sfc", "rb").read(), window)
    # {'write1 write2 write2 poll2 read2 read2': 2, ...}

That shape is the piece nothing else can supply. The part gives the console no
way to ask how many bytes an exchange moves, so a model has to be told, and the
only honest source is the code that already knows.

Nothing here executes anything. It walks a routine in the order the console would
and reports what each instruction reached.
"""

from . import conversation as conversation
from . import errors as errors
from . import walk as walk
from . import windows as windows
from .conversation import (
    POLL,
    READ,
    WRITE,
    Conversation,
    at,
    shapes,
    sites,
)
from .errors import UnknownPart
from .version import VERSION
from .walk import DEFAULT_LIMIT, through
from .windows import (
    DATA,
    STATUS,
    WINDOWS,
    Window,
    busiest,
    window_for,
)

__version__ = VERSION

__all__ = [
    "DATA",
    "DEFAULT_LIMIT",
    "POLL",
    "READ",
    "STATUS",
    "VERSION",
    "WINDOWS",
    "WRITE",
    "Conversation",
    "UnknownPart",
    "Window",
    "at",
    "busiest",
    "shapes",
    "sites",
    "through",
    "window_for",
]
