# Open questions

What this project does not know for certain, and what it would take to find out.

The largest entry is the first one, and it is the shape of the whole repository:
no manufacturer document on this machine gives the address lines a cartridge
board decodes for a coprocessor. Everything here about where a part answers is
inferred from what shipped drivers do.

The settled surface is what a cartridge sends, taken from the cartridge's own
code in the order the console runs it, across the 42 cartridges on hand. That is
strong evidence about those cartridges and it is not a document, and the
difference is what this file is for.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Why agreement across drivers cannot close these

Forty two independently written drivers agreeing is strong. One could be wrong;
forty two could not be wrong the same way. What that agreement still cannot say
is where a window **stops**, because a driver shows where a part answers and
never where it does not.

And the emulators that use the same windows are not a second witness. They were
written by people reading the same cartridge code this package reads, so counting
them as corroboration would be counting one piece of evidence twice. That is
written down here so nobody does.

## What would settle almost all of them

The DSP-1 application note from Nintendo's Book II, or a continuity reading
across a real cartridge board. Anything, in short, that did not come from reading
a driver.

## Where no document exists at all

### Which address lines a cartridge board decodes for a coprocessor.

**The document says.** Nothing. Nintendo's development manual, Book I, documents
the memory map and the header and not this. It was searched on 2026-08-21.

**What this project follows.** What the drivers do. Every driver read agrees with
the window this package uses for its part and layout.

**Why.** There is nothing above it. A driver was written by somebody who had the
part on a desk and had to make it work, which is the strongest evidence available
here, and it is still not a schematic.

**What would settle or reopen it.** The DSP-1 application note from Book II, a
board photograph, or a continuity reading.

### Where a window stops.

**The document says.** Nothing.

**What the drivers do.** Show where a part answers. They never show where it
stops answering, because a routine that never touched an address proves nothing
about that address.

**What this project follows.** The addresses the drivers reach, and no further.

**Why.** Extending a window past what was observed would be asserting an absence
from evidence that cannot carry one.

**What would settle or reopen it.** A continuity reading across a real board, or
a manufacturer note giving the decode.

### Every part with no cartridge on hand.

**The document says.** Nothing.

**What this project follows.** Neither. A window is listed only where a driver
was actually read. A part with no cartridge in the manifest gets no entry rather
than an entry copied from somewhere else, and a lookup for it raises instead of
guessing.

**What would settle or reopen it.** A cartridge carrying that part, added to the
manifest and read.

## Where the question is a scope boundary, not an unknown

### How long any of this takes.

**The document says.** Nothing about timing, and this package asks nothing about
it.

**What this project follows.** Neither. What one of these accesses costs the
console belongs to `snes-mapper-python`, and how long the part runs afterwards
belongs to whichever member models that part.

**What would settle or reopen it.** Nothing. This is a boundary rather than a
gap, and it is listed so a reader does not mistake the first for the second.

### The bank of an ordinary absolute access is assumed rather than read.

**The document says.** Nothing. This is about what this package can claim, not
about a part.

**What this project follows.** The routine's own bank, and it says so. A long
load or store spells all three bytes of its address, so the bank is read. An
ordinary absolute one spells two and takes the third from the data bank
register, which nothing here tracks. Until the ST018 every part this package
knew was reached long, so the question never came up; `Step.bank` answered
nothing for any other mode and a conversation carried on absolute accesses read
as no conversation at all.

It now answers, using the bank the routine executes in, and `Step.banked` and
`Conversation.banked` are how a caller tells a read bank from an assumed one. A
shape that mixed the two silently would claim more than it knows, which is why
the weaker claim is labelled rather than hidden.

**What would settle or reopen it.** Tracking the data bank register through a
walk, which needs an entry state that a walk starting at one routine does not
have.; A part whose driver sets the register somewhere this package can see.

### A call is not stepped into.

**The document says.** Nothing.

**What this project follows.** Neither. A walk runs past a `jsr` and reads the
instruction after it, which is what the console does, and it does not read the
callee. A routine reaching a part only through a helper is therefore read as two
routines rather than one.

**What exposed the half of this that is fixed.** The ST018. Its send routine at
file offset `0x006873` is `sep`, then `jsr` to a guard, then `sta $3802`, and a
walk that treated the call as leaving reported an empty conversation. `jsr` and
`jsl` were removed from the leaving set, and every shape recorded before that
was re-read from the cartridges rather than edited.

**What would settle or reopen it.** Stepping into the callee and returning to
the caller, which needs a return stack a straight walk does not keep. The cost
is the same as before: every recorded shape for a routine that calls out would
grow, so the cartridges have to be read again.

### A sweep cannot follow a computed jump.

**The document says.** Nothing.

**What this project follows.** Neither. `conversation.reached` starts at the
reset vector and follows every call, jump and branch whose destination is
spelled in the instruction. `jmp ($1234)` and its two indexed relatives name a
place to read the destination from rather than the destination, so the sweep
stops there.

**Why it is not treated as a gap in the evidence.** What the sweep reports is
still an instruction the console reaches. What it cannot do is prove the absence
of another routine, so a part it finds nothing for is unread rather than
uncontacted, and that difference is why this is written down.

**What would settle or reopen it.** Running the image rather than reading it,
which is a different package's job, or a jump table whose bounds this could
read. Neither is planned.

## What is not in question

So the boundary is visible rather than implied:

- **What a shipped cartridge sends.** Taken from its own code, instruction by
  instruction, in the order the console runs it. That is the one thing here no
  amount of poking the part from outside recovers.
- **The width of every access.** A store to a coprocessor moves one byte or two
  depending on the accumulator, and the accumulator's width is not in the
  instruction. The walk carries it through the `sep` and `rep` that set it, and a
  walk that did not would report an exchange the console never had.
- **That a routine is counted once.** A routine that writes and then reads is one
  exchange rather than two, so a site an earlier walk already stepped over does
  not start a conversation of its own.
- **That the file read was the file named.** Every cartridge is confirmed against
  all four of its digests before a byte of it is disassembled, because a file
  that is not the one named would be disassembled anyway and would report a
  protocol nobody's hardware has.

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **What the part answers.** This package reads what a cartridge says. What comes
  back belongs to the members that model those parts, and mixing the two would
  make each harder to test.
- **Anything executed.** Nothing here runs a program. A routine is walked from its
  first instruction to the first one that leaves.
- **Any cartridge content.** [`cartridges/README.md`](cartridges/README.md)
  carries filenames and digests. No part of any cartridge is reconstructible from
  anything here.
