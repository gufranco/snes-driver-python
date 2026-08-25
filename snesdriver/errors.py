"""Everything this package raises, in one place.

One module so a caller can see the whole set at once, and so `except` has
somewhere to import from. It imports nothing from the rest of the package, which
is what keeps it from ever closing a cycle: everything here raises, so everything
here imports this, and an import running the other way would make the order
modules happen to load in decide whether the package works at all.

It imports nothing from `mapper` or `mos65xx` either, which this package consumes
as submodules. That is a stronger statement than the rule asks for and it costs
nothing: a refusal this package makes is this package's, and inheriting one from
a member it depends on would make a caller's `except` depend on which of the
three raised.

One refusal is the whole set, because this package reads rather than decides. A
routine that reaches an address no window covers is a routine that talks to
something else, which is an answer rather than a fault.
"""

from __future__ import annotations


class UnknownPart(Exception):
    """No part goes by that name, so there is no window to look through.

    Raised rather than answered with nothing, because nothing is already the
    answer to a different question: a part that exists and does not answer under
    the layout asked about. Returning it for a name nobody recognises would make
    a typo indistinguishable from a real absence.

    The message names the parts that would have worked, because a refusal that
    does not costs the caller a search through the source.
    """
