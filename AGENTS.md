# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

A coprocessor's protocol is written down in exactly one place: the code the
cartridge runs to drive it. This reads that code. It walks a routine
instruction by instruction with a 65816 disassembler, reports which accesses
reached the part and how wide each was, and hands back a shape. Nothing here
executes anything and nothing here guesses.

## The authority ladder

Every factual question is answered by the highest rung that has an answer, and a
lower rung never overrules a higher one.

1. **Manufacturer documentation.** For this project that is the 65816 instruction
   set and the cartridge address decoding. Anything printed decides.
2. **The cartridge itself.** What a game sends is in the game. Read it.
3. **A recording from an independent implementation**, for behaviour nobody
   documented.
4. **Nothing else.** An emulator, an FPGA core, a wiki and a forum post are rung 3
   at best and rung 4 for anything printed. The sibling projects found a
   four-level stack where every implementation in the field carries sixteen,
   because somebody read the datasheet.

## The one rule that decides most questions

**A shape is read, never invented.**

The value of this project is that a shape is the cartridge's own sequence, in the
order the console runs it. A hand-written shape asks a question no hardware was
ever asked, and a model that answers it is answering nothing. If a test needs a
cartridge, it assembles one out of real instruction bytes rather than writing a
shape string by hand.

A shape carries accesses and widths and **no payload**. That is what makes it
publishable: no set of shapes reconstructs a byte of anybody's game.

## Every gate, in the order to run them

```bash
ruff format --check .                                  # formatting
ruff check .                                           # lint, zero warnings
mypy                                                   # types, strict
pnpm run format:check                                  # every JSON file
for f in snesdriver/*.test.py conformance/*.test.py; do python3 "$f"; done
python3 -m coverage report                             # fails below 100%
```

Coverage is collected by running each test file under `coverage run -a`, not by a
test runner:

```bash
python3 -m coverage erase
for f in snesdriver/*.test.py conformance/*.test.py; do python3 -m coverage run -a "$f"; done
python3 -m coverage report
```

This needs cartridges and reports as skipped rather than passed without them:

```bash
python3 conformance/against_cartridges.py
```

Exit 2 means the machine had nothing to read. That is not a failure and must
never be reported as one.

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
specs/current/           what this does now, as requirements with scenarios
```

## Adding a part

`snesdriver/windows.py` holds where each part answers, keyed by part and by the
layout the cartridge declares. Both matter: the same part answers at one place in
a low cartridge and another in a high one, and the address line that picks between
its two registers differs too. A new entry needs the bank range, the two ranges,
and a layout. It is a hardware fact, so it needs a source.

## What a change is expected to leave behind

A gate that would have caught the bug. A fix with no test that fails without it is
not finished.
