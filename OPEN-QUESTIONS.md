# Open questions

What this project does not know for certain, and what it would take to find out.

The largest entry is the first one, and it is the shape of the whole repository:
Nintendo's Book II prints the DSP's two windows and no manufacturer document
gives the address lines a cartridge board decodes for any other coprocessor.
Everything here about where the ST010, ST011, ST018 and OBC1 answer is inferred
from what shipped drivers do.

The settled surface is what a cartridge sends, taken from the cartridge's own
code in the order the console runs it, across the 42 cartridges on hand. That is
strong evidence about those cartridges and it is not a document, and the
difference is what this file is for.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Why agreement across drivers cannot close these

The drivers in 42 cartridges agreeing is strong, though a game released in
several regions carries one driver in each, so the independent witnesses are
fewer than 42. One could be wrong; all of them could not be wrong the same way.
What that agreement still cannot say is where a window **stops**, because a
driver shows where a part answers and never where it does not.

And the emulators that use the same windows are not a second witness. They were
written by people reading the same cartridge code this package reads, so counting
them as corroboration would be counting one piece of evidence twice. That is
written down here so nobody does.

## What would settle almost all of them

A continuity reading across a real cartridge board, or a document from Seta or
Nintendo for the parts Book II does not cover. Anything, in short, that did not
come from reading a driver. Book II has been read: it settles the DSP's windows
and nothing else here.

## Where no document exists at all

### Which address lines a cartridge board decodes for a coprocessor other than the DSP.

**The document says.** For the DSP, Book II's Figures 3-1-4 and 3-1-5 at pages
3-1-4 and 3-1-5: data at `8000H` and status at `C000H` to `FFFFH` in banks `30`
to `3F` and `B0` to `BF` under Mode 20, and data at `6000H` and status at
`7000H` to `7FFFH` in banks `00` to `0F` and `80` to `8F` under Mode 21. Those
two windows are marked verified and the package answers in the mirror banks the
figures print. For the ST010, ST011, ST018 and OBC1, nothing: Book I documents
the memory map and the header, and Book II has no chapter on any of them.

**What this project follows.** For the four undocumented parts, what the drivers
do. Every driver read agrees with the window this package uses for its part and
layout.

**Why.** There is nothing above it. A driver was written by somebody who had the
part on a desk and had to make it work, which is the strongest evidence available
here, and it is still not a schematic.

**What would settle or reopen it.** A Seta or Nintendo document for those
parts, a board photograph, or a continuity reading.

### Where a window other than the DSP's stops.

**The document says.** Nothing for the four undocumented parts. Book II's
figures give the DSP's whole span, every bank and both ranges.

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

**What running the image shows.** `conformance.executed` tracks the register
because it runs the code. Hayazashi Nidan Morita Shougi 2, run for 2,000,000
instructions from reset, reaches the ST018 from three instructions, and half of
the addresses they reach carry data bank `$2B` while the routine runs in bank
`$00`. Both banks sit inside the window, so the register answered is the same;
the bank the walk reports for them is still wrong.

**What would settle or reopen it.** Tracking the data bank register through a
walk, which needs an entry state that a walk starting at one routine does not
have, or reading shapes out of a run rather than a walk.

### The accumulator's width at a routine's entry is assumed rather than read.

**The document says.** Nothing. The width is whatever the caller left.

**What this project follows.** Neither. `shapes` walks every routine with an
8-bit accumulator at entry, and the walk carries the width through every `sep`
and `rep` after that.

**What that costs, measured.** F1-ROC II's ST010 start routine is entered 16
bits wide. Read 8 bits wide, the bytes at file offset `0x0D66`, `A9 06 80`,
decode as `lda #$06` and a branch, and the walk leaves with `write1 write1`.
Read 16 bits wide from the same entry, `at` reports
`write2 write2 write2 poll2 read2 read2`, and the third store is one word of
`$8006` to `$68:0020`. snes-st-python at commit `50c8414` recorded exactly that
store with a headless MAME write tap: the command byte and the start bit in one
16-bit write. Its `st010shapes.json` was read 8 bits wide and records the start
as a one-byte write.

**What would settle or reopen it.** Running the image rather than reading it, so
each routine is entered with the width its caller left, or tracking the width
from the vectors through every call.

### A call this cannot prove returns is stepped over rather than followed.

**The document says.** Nothing.

**What this project follows.** Neither. A walk now steps into a callee and comes
back, which is what the console does. It descends only into a callee it has first
walked to a return, because a call whose destination is a jump table or a block
of constants still disassembles: every byte is some opcode, and the walk would
spend its budget on nonsense and never come back for the caller's own accesses.

**What that cost when it was not conditional.** An F1-ROC II routine calls into a
region that decodes as `brk`. Descending into it lost the four accesses the
caller made afterwards, and the longest ST010 exchange fell from six accesses to
four. With the descent made conditional the same cartridge reads ten.

**What is left.** A helper that reaches the part and that this cannot prove
returns, because it exits through a computed jump or is longer than the probe
allows, is stepped over as before. Its accesses are then read as a routine of
their own rather than as part of the caller's exchange.

**What would settle or reopen it.** Reading shapes out of a run rather than a
walk. `conformance.executed` runs the image and follows every call the program
makes, so it reports which instructions reach the part; it does not yet turn a
run into shapes.

### A sweep cannot follow a computed jump.

**The document says.** Nothing.

**What this project follows.** Neither. `conversation.reached` starts at every
vector a low cartridge publishes and follows every call, jump and branch whose
destination is spelled in the instruction. `jmp ($1234)` and its two indexed
relatives name a place to read the destination from rather than the destination,
so the sweep stops there.

**How much that costs, measured.** Metal Combat seeded from reset alone reaches
1,675 instructions, and from all ten vectors 2,080. Through banks `$00` to `$3F`
alone neither run reaches the OBC1 once; through the mirror banks `$80` to `$BF`
the cartridge also uses, the walk from the vectors reaches it from 19
instructions, while a search of the same image for the bytes that spell a long
access finds 313 sites. That cartridge dispatches most of its driver through
something this cannot follow.

**Why it is not treated as a gap in the evidence.** What the sweep reports is
still an instruction the console reaches. What it cannot do is prove the absence
of another routine, so a part it finds nothing for is unread rather than
uncontacted, and that difference is why this is written down.

**What running the image shows.** `conformance.executed` follows every jump
because it runs the code. Metal Combat (USA), run for 2,000,000 instructions from
reset, reaches the OBC1 from 147 distinct instructions, every one an absolute
access from a routine running in bank `$80`. The walk from the vectors finds 19
of them and the byte search none, so 128 sit behind something the walk cannot
follow. The run answers every register but the blanking bits with 0, so what it
found is a floor.

**What would settle or reopen it.** Shapes read out of a run, or a jump table
whose bounds this could read.

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
