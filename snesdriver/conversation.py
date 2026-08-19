"""What a cartridge routine actually says to a part, read out of its own code.

A coprocessor's protocol is written down in exactly one place: the code the
cartridge runs to drive it. No datasheet survives for most of these parts, and
the emulators that talk to them were written by people who read the same code.
So this reads it too, rather than guessing from the outside.

What comes back is the shape of an exchange: how many bytes go each way, how wide
each access is, and whether the routine waits on the part between them. That is
the piece a model cannot supply and a caller cannot invent, because the part
gives no way to ask. On the DSP-1 the one bit the console can see stays asserted
throughout, so nothing about the exchange can be discovered by watching it.

Nothing here executes anything. It walks straight through a routine and reports
what each instruction reached, which is why a shape is evidence rather than a
guess: it is the cartridge's own sequence, read in the order the console runs it.
"""

import collections

from snesdriver import walk, windows

WRITE = "write"

READ = "read"

POLL = "poll"

LONG_STORE = 0x8F
LONG_LOAD = 0xAF
LONG_BYTES = 4


class Step:
    """One access a routine makes to the part."""

    def __init__(self, what, width, address):
        self.what = what
        self.width = width
        self.address = address

    def __repr__(self):
        return f"<{self.what} {self.width}>"


class Conversation:
    """Everything one routine says to a part, in the order it says it."""

    def __init__(self, steps, covered=()):
        self.steps = tuple(steps)
        self.covered = frozenset(covered)

    @property
    def written(self):
        return sum(step.width for step in self.steps if step.what == WRITE)

    @property
    def read(self):
        return sum(step.width for step in self.steps if step.what == READ)

    @property
    def polls(self):
        return any(step.what == POLL for step in self.steps)

    @property
    def shape(self):
        """The exchange as a string, so two routines can be compared by it."""
        return " ".join(f"{step.what}{step.width}" for step in self.steps)

    def __bool__(self):
        return bool(self.steps)

    def __repr__(self):
        return f"<Conversation {self.shape or 'nothing'}>"


def _reached(step, window):
    """Which register an instruction touched, or nothing if it touched none."""
    if step.bank is None:
        return None
    return window.reaches(step.bank, step.address)


def at(rom, offset, window, narrow=True, limit=walk.DEFAULT_LIMIT):
    """The conversation a routine at that offset has with a part at that window."""
    steps = []
    covered = []
    for step in walk.through(rom, offset, narrow=narrow, limit=limit):
        covered.append(step.offset)
        register = _reached(step, window)
        if register is None:
            continue
        if register == windows.STATUS:
            steps.append(Step(POLL, step.width, step.address))
        else:
            steps.append(Step(READ if step.reading else WRITE, step.width, step.address))
    return Conversation(steps, covered)


def sites(rom, window):
    """Every offset holding an instruction that reaches the part.

    A long load or store carries its whole address in the three bytes after the
    opcode, so the search is exact rather than heuristic: no other encoding puts
    that bank and that address there.
    """
    found = []
    for at_offset in range(len(rom) - LONG_BYTES + 1):
        if rom[at_offset] not in (LONG_STORE, LONG_LOAD):
            continue
        address = rom[at_offset + 1] | rom[at_offset + 2] << 8
        bank = rom[at_offset + 3]
        if window.reaches(bank, address):
            found.append(at_offset)
    return tuple(found)


def shapes(rom, window, narrow=True, limit=walk.DEFAULT_LIMIT):
    """Every distinct exchange in an image, and how many routines have it.

    A site that an earlier walk already stepped over does not start a
    conversation of its own. Every instruction touching the part is a site, but a
    routine that writes and then reads is one exchange rather than two, and
    walking from its middle would report the tail as though it were the whole.
    """
    counted = collections.Counter()
    seen = set()
    for offset in sites(rom, window):
        if offset in seen:
            continue
        found = at(rom, offset, window, narrow=narrow, limit=limit)
        seen |= found.covered
        if found:
            counted[found.shape] += 1
    return dict(counted)
