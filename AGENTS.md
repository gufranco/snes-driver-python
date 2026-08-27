# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

A coprocessor's protocol is written down in exactly one place: the code the
cartridge runs to drive it. This reads that code. It walks a routine
instruction by instruction with a 65816 disassembler, reports which accesses
reached the part and how wide each was, and hands back a shape. Nothing here
executes anything and nothing here guesses.

## The interface a caller drives

Nothing here is built and then driven. Every call is a question about a
cartridge's own code, and none of it executes anything.

- `window_for(part, layout)` gives the two addresses that part answers at under
  that layout, or nothing when it does not answer under it at all. A name no part
  goes by raises rather than answering nothing, because nothing is already the
  answer to the other question.
- `sites(rom, window)` is every instruction in the image that reaches the part.
- `at(rom, offset, window)` walks one routine and hands back the whole exchange:
  each access, where it landed, how wide it was, and the sites it accounted for.
- `shapes(rom, window)` is every distinct exchange in the image with how often
  each occurs.
- `through(rom, offset)` is the walk itself, instruction by instruction, for a
  caller who wants the steps rather than the exchange.

Everything the package raises lives in
[`snesdriver/errors.py`](snesdriver/errors.py) and nowhere else, and that module
imports nothing from this package, nor from either member it consumes. A refusal
this package makes is this package's, and inheriting one would make a caller's
`except` depend on which of the three raised.

There is no clock. Nothing here is a model of a part.

## The authority ladder

1. **Manufacturer documentation.** For this project that is the 65816 instruction
   set and the cartridge address decoding. Anything printed decides.
2. **The cartridge itself.** What a game sends is in the game. Read it.
3. **A recording from an independent implementation**, for behaviour nobody
   documented.
4. **Nothing else.** An emulator, an FPGA core, a wiki and a forum post are rung 3
   at best and rung 4 for anything printed. The sibling projects found a
   four-level stack where every implementation in the field carries sixteen,
   because somebody read the datasheet.

## What is settled and what is not

**Settled: what a shipped cartridge sends.** Read across the 36 DSP cartridges on
hand, each confirmed against all four of its digests before a byte of it is
disassembled.

**Settled: the width of every access.** The walk carries the accumulator's width
through the `sep` and `rep` that set it, which is the part that cannot be skipped
and the part a naive reader gets wrong on every store.

**Settled: that a routine is counted once.** A site an earlier walk already
stepped over does not start a conversation of its own.

**Not settled: 7 things**, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with
what would close it. Three of them are the same shape: no manufacturer document
gives any of these windows, so everything about where a part answers rests on
what shipped drivers do. Do not close one by argument, and do not close one with
an emulator.

## The one rule that decides most questions

**A shape is read, never invented.**

The value of this project is that a shape is the cartridge's own sequence, in the
order the console runs it. A hand-written shape asks a question no hardware was
ever asked, and a model that answers it is answering nothing. If a test needs a
cartridge, it assembles one out of real instruction bytes rather than writing a
shape string by hand.

A shape carries accesses and widths and **no payload**. That is what makes it
publishable: no set of shapes reconstructs a byte of anybody's game.

## Adding a part

`snesdriver/windows.py` holds where each part answers, keyed by part and by the
layout the cartridge declares. Both matter: the same part answers at one place in
a low cartridge and another in a high one, and the address line that picks between
its two registers differs too. A new entry needs the bank range, the two ranges,
and a layout. It is a hardware fact, so it needs a source.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
mypy
pnpm run format:check
python3 -m coverage erase
for file in $(find snesdriver conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Then the throughput floor, which runs outside the coverage step because a tracer
costs about ten times what the walk does:

```bash
python3 -m conformance.speed
```

This one needs cartridges and reports as skipped rather than passed without them:

```bash
python3 -m conformance.against_cartridges
```

Exit 2 means the machine had nothing to read. That is not a failure and must
never be reported as one.

The submodules need no `PYTHONPATH`. The disassembler and the memory map are put
on the path by the modules that need them, so a checkout works as it stands and
CI sets nothing. What they do need is to be there: a checkout without
`--recurse-submodules` fails at import, which is a different failure and says so.

Everything under `conformance/` runs as a module. Run as a script, its own
directory goes on the import path and a file there shadows any standard library
module of the same name.

## Conventions that are not negotiable

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source, ever. Docstrings carry the reasoning |
| Test layout | `<module>.test.py` beside the module it covers |
| Test structure | Arrange, blank line, one act, blank line, assert. No section labels |
| Coverage | 100% statements and branches, enforced |
| Types | `mypy` at strict, plus every optional error class the version offers |
| Commits | [Conventional Commits](https://www.conventionalcommits.org/); subject under 50 characters |
| Releases | semantic-release from `main`; never tag by hand |
| Cartridges | Never committed, never vendored, never encoded, never generated |

## Layout

```
snesdriver/
  walk.py         one instruction at a time, and what each reached
  conversation.py the accesses a routine makes, as a shape
  windows.py      where each part answers, per cartridge layout
conformance/
  cartridges.py          finding and confirming a user's own library
  against_cartridges.py  reading every cartridge present
mos65xx-python/          the disassembler, as a submodule
snes-mapper-python/      the header and address decoding, as a submodule
cartridges/              a user's own copies; nothing here is ever committed
```

## Things that will bite you

**Prettier walks into submodules, and their files are not this project's to
format.** A dependency records what its own recorder writes, in that recorder's
format, and its ignore file exempts it. This project's ignore file has to exempt
the whole submodule tree instead, or the gate fails on a file no change here
touched and no change here may fix.

**Run the suite as a machine that holds nothing.** A test that reaches a default
which opens a real cartridge passes on a workstation holding a library and fails
on a runner, and the local run gives no hint:

```bash
EMPTY=$(mktemp -d)
for f in snesdriver/*.test.py conformance/*.test.py; do
  SNES_CARTRIDGE_DIR="$EMPTY" python3 "$f" || echo "FAILED $f"
done
```

**Put this repository's own root on the path ahead of any dependency's.** Both
this project and the mapper carry a package called `conformance`, so whichever
root comes first decides which one `from conformance import ...` finds. Inserting
a dependency's root last silently hands this project its dependency's modules, and
the symptom is not an import error: it is a runner that reads zero cartridges and
a suite that fails on attributes that exist in the wrong repository.

**The directory a user keeps games in is called `cartridges`, and so is a module
in `conformance`.** A bare `import cartridges` is ambiguous: the type checker
resolves it to the directory, which is an implicit namespace package with nothing
in it, and every attribute reads as missing. Import it package-qualified,
`from conformance import cartridges`, which is unambiguous at runtime and to the
checker.

**Run the suite on the oldest Python supported, not only the newest.** Annotations
are evaluated eagerly before 3.14 and lazily from 3.14 on, so a file naming a type
imported only under `TYPE_CHECKING` imports fine on 3.14 and raises on 3.12. Every
file that does this carries `from __future__ import annotations`.

**Coverage that depends on what the machine holds is not coverage.** Tests that
need a cartridge write one. The only thing outside the gate is the test class whose
subject is a real library, and it says so where it sits.

**Never commit a cartridge or any fragment of one.** What may be committed is a
digest, which identifies a file and reconstructs nothing, and a shape, which
carries no payload.

**Only retail dumps.** A ROM hack is somebody's edit, and a protocol read out of
one is not a protocol any hardware spoke.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them, so it is the list of things that have
actually gone wrong here rather than a list of good intentions. Read it before
adding a surface, and read it again before saying a change is done.

**A submodule pin is a claim about this package's behaviour until proven
otherwise.** Two of them are on the path here. Run the suite against the newer
copy before committing a bump, and when the output changes, find out which
upstream commit changed it and why before touching anything that records what the
output should be. A digest updated to make a check pass is the failure this whole
standard exists to prevent.

A change to `FAMILY.md` is a change to every member. Nothing here can catch it
being made in one of them and forgotten in the others, because a test in this
repository cannot see the others, so the check is a command rather than a suite:

```sh
shared() { sed '/^\*Everything above this line/q' "$1"; }

grep -o 'github\.com/[^/]*/\([a-z0-9-]*\))' FAMILY.md | sed 's|.*/||; s|)||' | sort -u |
while read -r member; do
  other="../$member/FAMILY.md"
  [ -f "$other" ] || { echo "not on this machine: $member"; continue; }
  cmp <(shared FAMILY.md) <(shared "$other") && echo "match: $member"
done
```

The members come from the table at the top of `FAMILY.md` rather than from a glob
over the parent directory. The two submodules under this repository carry copies
of that file too, and each is a member in its own right rather than a copy to
compare against from here.

Two rules from that file are worth repeating because they are the ones skipped
most often:

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it.

**Silence and success produce the same output.** A sweep that read no cartridge
exits differently from one that read a library, and that difference is the exit
code above rather than a bare pass.

## What a change is expected to leave behind

A gate that would have caught the bug. A fix with no test that fails without it is
not finished.
